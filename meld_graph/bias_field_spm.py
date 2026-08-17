import os
import subprocess
import shutil
import tempfile

def bias_field_correct_SPM(input_image_path, output_image_path):
    with tempfile.TemporaryDirectory() as workdir:

        # copy input image to workdir
        temp_input_path = os.path.join(workdir, os.path.basename(input_image_path))
        shutil.copy2(input_image_path, temp_input_path)

        gzip = False
        # check if input is gzipped
        if input_image_path.endswith('.gz'):
            gzip = True
            # gunzip for SPM
            unzipped_input_path = temp_input_path[:-3]
            subprocess.run(f"gunzip {temp_input_path}", shell=True, executable='/bin/bash', check=True)
            temp_input_path = unzipped_input_path

        matlab_script_path = os.path.join(workdir,"spm_script.m")
        matlab_code = """
matlabbatch{1}.spm.spatial.preproc.channel.vols = {'INPUT_PATH,1'};
matlabbatch{1}.spm.spatial.preproc.channel.biasreg = 0.0001;
matlabbatch{1}.spm.spatial.preproc.channel.biasfwhm = 60;
matlabbatch{1}.spm.spatial.preproc.channel.write = [0 1];
matlabbatch{1}.spm.spatial.preproc.tissue(1).tpm = {'/opt/spm/spm25_mcr/spm25/tpm/TPM.nii,1'};
matlabbatch{1}.spm.spatial.preproc.tissue(1).ngaus = 1;
matlabbatch{1}.spm.spatial.preproc.tissue(1).native = [0 0];
matlabbatch{1}.spm.spatial.preproc.tissue(1).warped = [0 0];
matlabbatch{1}.spm.spatial.preproc.tissue(2).tpm = {'/opt/spm/spm25_mcr/spm25/tpm/TPM.nii,2'};
matlabbatch{1}.spm.spatial.preproc.tissue(2).ngaus = 1;
matlabbatch{1}.spm.spatial.preproc.tissue(2).native = [0 0];
matlabbatch{1}.spm.spatial.preproc.tissue(2).warped = [0 0];
matlabbatch{1}.spm.spatial.preproc.tissue(3).tpm = {'/opt/spm/spm25_mcr/spm25/tpm/TPM.nii,3'};
matlabbatch{1}.spm.spatial.preproc.tissue(3).ngaus = 2;
matlabbatch{1}.spm.spatial.preproc.tissue(3).native = [0 0];
matlabbatch{1}.spm.spatial.preproc.tissue(3).warped = [0 0];
matlabbatch{1}.spm.spatial.preproc.tissue(4).tpm = {'/opt/spm/spm25_mcr/spm25/tpm/TPM.nii,4'};
matlabbatch{1}.spm.spatial.preproc.tissue(4).ngaus = 3;
matlabbatch{1}.spm.spatial.preproc.tissue(4).native = [0 0];
matlabbatch{1}.spm.spatial.preproc.tissue(4).warped = [0 0];
matlabbatch{1}.spm.spatial.preproc.tissue(5).tpm = {'/opt/spm/spm25_mcr/spm25/tpm/TPM.nii,5'};
matlabbatch{1}.spm.spatial.preproc.tissue(5).ngaus = 4;
matlabbatch{1}.spm.spatial.preproc.tissue(5).native = [0 0];
matlabbatch{1}.spm.spatial.preproc.tissue(5).warped = [0 0];
matlabbatch{1}.spm.spatial.preproc.tissue(6).tpm = {'/opt/spm/spm25_mcr/spm25/tpm/TPM.nii,6'};
matlabbatch{1}.spm.spatial.preproc.tissue(6).ngaus = 2;
matlabbatch{1}.spm.spatial.preproc.tissue(6).native = [0 0];
matlabbatch{1}.spm.spatial.preproc.tissue(6).warped = [0 0];
matlabbatch{1}.spm.spatial.preproc.warp.mrf = 1;
matlabbatch{1}.spm.spatial.preproc.warp.cleanup = 1;
matlabbatch{1}.spm.spatial.preproc.warp.reg = [0 0 0.1 0.01 0.04];
matlabbatch{1}.spm.spatial.preproc.warp.affreg = 'mni';
matlabbatch{1}.spm.spatial.preproc.warp.fwhm = 0;
matlabbatch{1}.spm.spatial.preproc.warp.samp = 3;
matlabbatch{1}.spm.spatial.preproc.warp.write = [0 0];
matlabbatch{1}.spm.spatial.preproc.warp.vox = NaN;
matlabbatch{1}.spm.spatial.preproc.warp.bb = [NaN NaN NaN
                                              NaN NaN NaN];
spm('defaults', 'FMRI');
spm_jobman('run', matlabbatch);
        """
        # Replace placeholder with actual paths, better than f-strings because
        # we don't need to escape all the braces
        matlab_code = matlab_code.replace('INPUT_PATH', temp_input_path)

        with open(matlab_script_path, 'w') as f:
            f.write(matlab_code)

        print(f"MATLAB script written to: {matlab_script_path}")

        cmd = f"spm script {matlab_script_path}"
        subprocess.run(cmd, shell=True, executable='/bin/bash', check=True)

        outfile = os.path.join(os.path.dirname(temp_input_path), 'm' + os.path.basename(temp_input_path))

        if gzip:
            # gzip the output
            subprocess.run(f"gzip {outfile}", shell=True, executable='/bin/bash', check=True)
            outfile += '.gz'

        shutil.move(outfile, output_image_path)
        print(f"Output saved to: {output_image_path}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Run SPM bias field correction.")
    parser.add_argument("--input_image_path", type=str, required=True, help="Path to the input image to be segmented.")
    parser.add_argument("--output_image_path", type=str, required=True, help="Path to save the output segmented image.")
    args = parser.parse_args()

    bias_field_correct_SPM(args.input_image_path, args.output_image_path)
