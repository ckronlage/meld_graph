<img src="https://raw.githubusercontent.com//MELDProject/meld_graph/main/docs/images/MELD_logo.png" alt="MELD logo" width="100" align="left"/> 


# MELD Graph 

> **This is a fork** of [MELDProject/meld_graph](https://github.com/MELDProject/meld_graph) v2.2.6 and adds a flag for processing **ultra-high field (7T) MRI** data. Everything not 7T-specific is unchanged - follow the documentation in the original repository below for installation, data preparation, harmonisation and interpretation of the results.

## Disclaimer

The MELD surface-based graph FCD detection algorithm is intended for research purposes only and has not been reviewed or approved by the Medicines and Healthcare products Regulatory Agency (MHRA), European Medicine Agency (EMA) or by any other agency. Any clinical application of the software is at the sole risk of the party engaged in such application. There is no warranty of any kind that the software will produce useful results in any way. Use of the software is at the recipient's own risk.

## Running on ultra-high field (7T) data

This section describes **only what differs in this fork if you would like to use the adapted preprocessing and segmentation**. Data preparation, harmonisation and interpretation of results is otherwise unchanged.

**This version is only supported to be run via a container image (Docker/Singularity/Apptainer)** because of the SynthStrip and SPM dependencies that are otherwise complicated to install. 

### 1. Build this fork's container image

The UHF pipeline needs two tools that the published `meldproject/meld_graph` image does not contain, both added to the `Dockerfile` in this fork:

- **SPM 25** with the MATLAB Runtime R2024b (for bias field correction).
- **SynthStrip** from FreeSurfer 8.0.0 with `synthstrip.nocsf.1.pt` model weights (for skullstripping).

Build this fork's image:

```bash
docker build -t meld_graph:uhf .
```

And point the docker `compose.yml` at it:
```yaml
services:
  meld_graph:
    image: meld_graph:uhf
```
Or convert to an Apptainer image:
```
apptainer build meld_graph.sif docker-daemon://meld_graph:uhf 
```

Everything else about the container setup (mounting the data folder, the FreeSurfer and MELD licences, etc.) follows the original installation instruction.

### 2. Denoise MP2RAGE UNI input image (optional but recommended)

MP2RAGE uniform (UNI) images have a noisy background, which can impact with segmentation. `scripts/uhf/mp2rage_denoise.py` implements the "robust combination" of [O'Brien et al. (2014)](https://doi.org/10.1371/journal.pone.0099676). Run it before the pipeline and use the denoised UNI as the T1 of your BIDS dataset:

```bash
python scripts/uhf/mp2rage_denoise.py \
    --uni  sub-01_UNI.nii.gz \
    --inv1 sub-01_inv1.nii.gz \
    --inv2 sub-01_inv2.nii.gz \
    --out  sub-01_UNI_denoised.nii.gz \
    --beta 0.1
```

`--beta` is a regularization parameter, higher values will remove more noise but re-introduce bias field inhomogeneity.

### 3. Run the MELD-graph pipeline with `--uhf_highres`

Prepare your data as usual, then add `--uhf_highres` to the standard command, e.g.:
```bash
DOCKER_USER="$(id -u):$(id -g)" docker compose run meld_graph \
    python scripts/new_patient_pipeline/new_pt_pipeline.py \
    -id sub-01 --uhf_highres
```

The flag is available both on `new_pt_pipeline.py` and on `run_script_segmentation.py`. It replaces the single `recon-all -all` call with a pipeline adapted to high-resolution, non-uniform 7T data:

1. **Intensity rescaling** — MP2RAGE UNI volumes usually span `[-0.5, 0.5]`. Negative values break SPM and FreeSurfer (the gray–white contrast feature is computed from the unnormalised `rawavg.mgz`)
2. **Bias field correction** with SPM (`meld_graph/bias_field_spm.py`).
3. **`recon-all -autorecon1 -noskullstrip -hires`**, with a per-subject expert options file reducing `mris_inflate` to 50 iterations, which `-hires` requires.
4. **Skull stripping with `mri_synthstrip --no-csf`**, which should be more robust than FreeSurfer's watershed stripping on 7T contrast.
5. **`recon-all -autorecon2 -autorecon3 -hires`**, with `-FLAIR`/`-FLAIRpial` when a FLAIR is available.

**Limitations.** `--uhf_highres` cannot be combined with:

- `--parallelise` — subjects are processed one at a time; use `--threads` to speed up the individual `recon-all` calls instead.
- `--fastsurfer` — the pipeline is built on `recon-all -hires`, which FastSurfer does not provide.

Both combinations raise `NotImplementedError`.

**Intermediate files**, useful for QC and when restarting a failed run:

- `output/preproc/<subject>/rescaled_*.nii.gz` and `bfc_*.nii.gz` — the rescaled and bias field corrected T1 handed to `recon-all`.

