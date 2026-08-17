## Expensive calls that don't change go up top. See https://docs.docker.com/build/cache/

# freesurfer stage 
FROM mambaorg/micromamba:latest AS micromamba
USER root

ENV MAMBA_ROOT_PREFIX="/opt/conda"
ENV MAMBA_EXE="/bin/micromamba"

#Update ubuntu.
RUN apt-get -y update && apt-get install --no-install-recommends -y wget gcc g++ && apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

RUN mkdir /tmp/pkg
WORKDIR /tmp

COPY ./environment.yml ./environment.yml

# Create the meld_graph environment
RUN micromamba create -y -f environment.yml \
    && micromamba clean -afy

# Create the synthstrip environment
RUN apt-get -y update && apt-get install --no-install-recommends -y git && apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*
COPY <<EOT synthstrip.yml
name: synthstrip
channels:
  - conda-forge
dependencies:
  - python=3.10.12
  - pip
  - pip:
    - torch==2.1.2
    - surfa==0.6.1
EOT
RUN micromamba create -y --name synthstrip -f synthstrip.yml


# meld graph stage
FROM debian:12-slim AS meldgraph
RUN mkdir -p /opt/freesurfer-7.2.0

#Update ubuntu.
RUN apt-get -y update && apt-get install --no-install-recommends -y wget aria2 ca-certificates && apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Download freesurfer
RUN aria2c -x 16 -s 16 -k 1M --check-certificate=false -c https://surfer.nmr.mgh.harvard.edu/pub/dist/freesurfer/7.2.0/freesurfer-linux-ubuntu18_amd64-7.2.0.tar.gz && \
    tar -xzf freesurfer-linux-ubuntu18_amd64-7.2.0.tar.gz -C /opt/freesurfer-7.2.0 --owner root --group root --no-same-owner --strip-components 1 --keep-newer-files \
    --exclude='average/mult-comp-cor' \
    --exclude='lib/cuda' \
    --exclude='lib/qt' \
    --exclude='subjects/V1_average' \
    --exclude='subjects/bert' \
    --exclude='subjects/cvs_avg35' \
    --exclude='subjects/cvs_avg35_inMNI152' \
    --exclude='subjects/fsaverage3' \
    --exclude='subjects/fsaverage4' \
    --exclude='subjects/fsaverage5' \
    --exclude='subjects/fsaverage6' \
    --exclude='trctrain' && \
    rm freesurfer-linux-ubuntu18_amd64-7.2.0.tar.gz

ENV DEBIAN_FRONTEND="noninteractive"

#Install the prerequisite software
RUN apt-get -y update && \
    apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    time \
    wget \
    git \
    tcsh \
    vim \
    csh \
    procps \
    bzip2 \
    ca-certificates \
    bc \
    python3 \
    file \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# #Modify the environment with Freesurfer paths
ENV PATH=/opt/freesurfer-7.2.0/bin:$PATH
RUN echo "PATH=/opt/freesurfer-7.2.0/bin:$PATH" >> ~/.bashrc
ENV FREESURFER_HOME=/opt/freesurfer-7.2.0
RUN echo "FREESURFER_HOME=/opt/freesurfer-7.2.0" >> ~/.bashrc
RUN echo "FS_LICENSE=/license.txt" >> ~/.bashrc

# Install Fastsurfer
RUN  mkdir -p /fastsurfer \
&& git clone --branch v1.1.2 https://github.com/Deep-MI/FastSurfer.git /opt/fastsurfer-v1.1.2
RUN echo "export PYTHONPATH=\"\${PYTHONPATH}:$PWD\"" >> ~/.bashrc
ENV FASTSURFER_HOME=/opt/fastsurfer-v1.1.2
RUN echo "FASTSURFER_HOME=/opt/fastsurfer-v1.1.2" >> ~/.bashrc

# Add conda to path
ENV CONDA_DIR /opt/conda
ENV PATH=$CONDA_DIR/bin:$PATH

# Copy the micromamba bin and env
COPY --from=micromamba /bin/micromamba /bin/micromamba
COPY --from=micromamba /opt/conda/envs/meld_graph /opt/conda/envs/meld_graph

ENV MAMBA_ROOT_PREFIX="/opt/conda"
ENV MAMBA_EXE="/bin/micromamba"


# Install synthstrip
COPY --from=micromamba /opt/conda/envs/synthstrip /opt/conda/envs/synthstrip
# download code and weights
RUN mkdir -p /opt/synthstrip/models
#RUN wget https://surfer.nmr.mgh.harvard.edu/docs/synthstrip/requirements/synthstrip.1.pt \
#    -O /opt/synthstrip/models/synthstrip.1.pt
RUN wget https://surfer.nmr.mgh.harvard.edu/docs/synthstrip/requirements/synthstrip.nocsf.1.pt \
    -O /opt/synthstrip/models/synthstrip.nocsf.1.pt
#RUN wget https://surfer.nmr.mgh.harvard.edu/docs/synthstrip/requirements/synthstrip.infant.1.pt \
#    -O /opt/synthstrip/models/synthstrip.infant.1.pt
RUN wget https://raw.githubusercontent.com/freesurfer/freesurfer/refs/tags/v8.0.0/mri_synthstrip/mri_synthstrip \
    -O /opt/synthstrip/mri_synthstrip
# remove first line (sets env vars)
RUN sed -i '1d' /opt/synthstrip/mri_synthstrip
COPY <<EOT /usr/local/bin/mri_synthstrip
#!/bin/bash
export FREESURFER_HOME=/opt/synthstrip
micromamba run -n synthstrip python /opt/synthstrip/mri_synthstrip \$@
EOT
RUN chmod +x /usr/local/bin/mri_synthstrip

# Install spm standalone with matlab runtime
# adapted from official SPM standalone Dockerfile
# (https://github.com/spm/spm-docker/blob/main/matlab/Dockerfile)
ARG MATLAB_VERSION=R2024b
ARG AGREE_TO_MATLAB_RUNTIME_LICENSE=yes
ARG SPM_VERSION=25
ARG SPM_RELEASE=25.01.02

RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get -y install \
    unzip xorg wget \
    && apt-get clean \
    && rm -rf \
    /tmp/hsperfdata* \
    /var/*/apt/*/partial \
    /var/lib/apt/lists/* \
    /var/log/apt/term*

ENV LD_LIBRARY_PATH=/usr/local/MATLAB/MATLAB_Runtime/${MATLAB_VERSION}/runtime/glnxa64:/usr/local/MATLAB/MATLAB_Runtime/${MATLAB_VERSION}/bin/glnxa64:/usr/local/MATLAB/MATLAB_Runtime/${MATLAB_VERSION}/sys/os/glnxa64:/usr/local/MATLAB/MATLAB_Runtime/${MATLAB_VERSION}/sys/opengl/lib/glnxa64:/usr/local/MATLAB/MATLAB_Runtime/${MATLAB_VERSION}/extern/bin/glnxa64:$LD_LIBRARY_PATH
ENV MCR_INHIBIT_CTF_LOCK=1
ENV SPM_HTML_BROWSER=0

# Install SPM Standalone in /opt/spm/
# Running SPM once with "function exit" tests the succesfull installation *and*
# extracts the ctf archive which is necessary if singularity is going to be
# used later on, because singularity containers are read-only.
# Also, set +x on the entrypoint for non-root container invocations
RUN wget --no-check-certificate --progress=bar:force -P /opt https://github.com/spm/spm/releases/download/${SPM_RELEASE}/spm_standalone_${SPM_RELEASE}_Linux.zip \
    && unzip -q /opt/spm_standalone_${SPM_RELEASE}_Linux.zip -d /opt \
    && rm -f /opt/spm_standalone_${SPM_RELEASE}_Linux.zip \
    && mv /opt/spm_standalone /opt/spm \
    && /opt/runtime_installer/Runtime_${MATLAB_VERSION}_for_spm_standalone_${SPM_RELEASE}.install -agreeToLicense ${AGREE_TO_MATLAB_RUNTIME_LICENSE} \
    && /opt/spm/spm${SPM_VERSION} function exit \
    && chmod +x /opt/spm/spm${SPM_VERSION} \
    && ln -s /opt/spm/spm${SPM_VERSION} /usr/local/bin/spm


RUN mkdir /app

# Define working directory
WORKDIR /app

# Add meld_graph code
COPY . .

# The core change: install dependencies in the correct order.
RUN micromamba run -n meld_graph /bin/bash -c "pip install --no-cache-dir torch==1.10.0 torchvision==0.11.1 && pip install -e . && pip install torch-scatter -f https://data.pyg.org/whl/torch-1.10.0.html && pip install torch-geometric==2.4.0 && pip install captum==0.6.0" \
    && micromamba shell init -s bash \
    && echo "micromamba activate meld_graph" >> $HOME/.bashrc
    
ENV PATH="/opt/conda/envs/meld_graph/bin:$PATH"

# Add data folder to docker
RUN mkdir /data

# Create a cache directory for fastsurfer, otherwise permission denied
RUN mkdir /.cache
RUN chmod -R 777 /.cache

# Create a cache directory for freesurfer, otherwise permission denied
RUN mkdir /matlab
RUN chmod -R 777 /matlab

# Set permissions for the entrypoint
RUN chmod +x entrypoint.sh

ENV KEEP_DATA_PATH=1
ENV SILENT=1

ENTRYPOINT ["/bin/bash","entrypoint.sh"]
