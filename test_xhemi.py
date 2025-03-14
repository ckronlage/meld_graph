import os
import numpy as np
import subprocess
import nibabel as nib


def main():
    FREESURFER_SUBJ_DIR = '/home/ckronlage/meld_graph_fork/freesurfer_testdir/testsubj'

    os.makedirs(os.path.join(FREESURFER_SUBJ_DIR, 'test_xhemi'), exist_ok=True)
    SUBJECTS_DIR = os.path.join(os.path.sep,*FREESURFER_SUBJ_DIR.split(os.path.sep)[:-1])

    testvol = nib.load(os.path.join(FREESURFER_SUBJ_DIR, 'mri', 'orig.mgz'))
    data = testvol.get_fdata()
    
    # 3d random cubes with size CUBE_SIZE
    CUBE_SIZE = 10
    cube = np.ones((CUBE_SIZE, CUBE_SIZE, CUBE_SIZE))
    testdata = np.random.randint(low=0, high=2, size=[np.ceil(d / CUBE_SIZE).astype(np.int32) for d in data.shape])
    testdata = np.kron(testdata, cube)
    # crop to original size
    testdata = testdata[:data.shape[0], :data.shape[1], :data.shape[2]]


    # save grid as nifti
    vol = os.path.join(FREESURFER_SUBJ_DIR, 'test_xhemi', 'testvol.nii.gz')
    nib.save(nib.Nifti1Image(testdata, testvol.affine), vol)

    compare_sampling_back_fsaverage_sym_to_native(FREESURFER_SUBJ_DIR, SUBJECTS_DIR, vol)
    compare_sampling_to_fsaverage_sym_lh(FREESURFER_SUBJ_DIR, SUBJECTS_DIR, vol)


def compare_sampling_back_fsaverage_sym_to_native(FREESURFER_SUBJ_DIR, SUBJECTS_DIR, vol):
    # sample rh from vol to surf
    surf_nativespace = os.path.join(FREESURFER_SUBJ_DIR, 'test_xhemi', 'testvol_rh.mgh')
    command = f"SUBJECTS_DIR={SUBJECTS_DIR} mri_vol2surf --src {vol} --out {surf_nativespace} --hemi rh --regheader testsubj --projfrac 0.0"
    subprocess.run(command, shell=True, cwd=os.getcwd(), executable='/bin/bash')
        
    # resample to fsaverage_sym lh
    surf_fsaverage_sym = os.path.join(FREESURFER_SUBJ_DIR, 'test_xhemi', 'testvol_rh_fsaverage_sym_lh.mgh')
    command = f"SUBJECTS_DIR={SUBJECTS_DIR} mris_apply_reg --src {surf_nativespace} --trg {surf_fsaverage_sym} --streg {FREESURFER_SUBJ_DIR}/xhemi/surf/lh.fsaverage_sym.sphere.reg {SUBJECTS_DIR}/fsaverage_sym/surf/lh.sphere.reg"
    subprocess.run(command, shell=True, cwd=os.getcwd(), executable='/bin/bash')

        
    # sample back to native space, method 1 (register_back_to_xhemi.py)
    # step 1
    surf_back_nativespace_method1_intermediate = os.path.join(FREESURFER_SUBJ_DIR, 'test_xhemi', 'testvol_rh_back_method1_intermediate.mgh')
    command = f'SUBJECTS_DIR={SUBJECTS_DIR} mris_apply_reg --src {surf_fsaverage_sym} --trg {surf_back_nativespace_method1_intermediate} --streg {SUBJECTS_DIR}/fsaverage_sym/surf/lh.sphere.reg {SUBJECTS_DIR}/fsaverage_sym/surf/rh.sphere.left_right --nnf'
    subprocess.run(command, shell=True, cwd=os.getcwd(), executable='/bin/bash')

    # step 2
    surf_back_nativespace_method1 = os.path.join(FREESURFER_SUBJ_DIR, 'test_xhemi', 'testvol_rh_back_method1.mgh')
    command = f'SUBJECTS_DIR={SUBJECTS_DIR} mris_apply_reg --src {surf_back_nativespace_method1_intermediate} --trg {surf_back_nativespace_method1} --streg {SUBJECTS_DIR}/fsaverage_sym/surf/rh.sphere.reg {FREESURFER_SUBJ_DIR}/surf/rh.sphere.reg --nnf'
    subprocess.run(command, shell=True, cwd=os.getcwd(), executable='/bin/bash')

    # sample back to native space, method 2 (one step)
    surf_back_nativespace_method2 = os.path.join(FREESURFER_SUBJ_DIR, 'test_xhemi', 'testvol_rh_back_method2.mgh')
    command = f'SUBJECTS_DIR={SUBJECTS_DIR} mris_apply_reg --src {surf_fsaverage_sym} --trg {surf_back_nativespace_method2} --streg {SUBJECTS_DIR}/fsaverage_sym/surf/lh.sphere.reg {FREESURFER_SUBJ_DIR}/xhemi/surf/lh.fsaverage_sym.sphere.reg --nnf'
    subprocess.run(command, shell=True, cwd=os.getcwd(), executable='/bin/bash')

    # visualize
    command = f'freeview -v {vol} -f {FREESURFER_SUBJ_DIR}/surf/rh.white:overlay={surf_nativespace}:overlay={surf_back_nativespace_method1}:overlay={surf_back_nativespace_method2}:edgecolor=overlay'
    subprocess.run(command, shell=True, cwd=os.getcwd(), executable='/bin/bash')

def compare_sampling_to_fsaverage_sym_lh(FREESURFER_SUBJ_DIR, SUBJECTS_DIR, vol):
    # sample lh from vol to surf
    surf_nativespace = os.path.join(FREESURFER_SUBJ_DIR, 'test_xhemi', 'testvol_lh.mgh')
    command = f"SUBJECTS_DIR={SUBJECTS_DIR} mri_vol2surf --src {vol} --out {surf_nativespace} --hemi lh --regheader testsubj --projfrac 0.0"
    subprocess.run(command, shell=True, cwd=os.getcwd(), executable='/bin/bash')
        
    # resample to fsaverage_sym lh method 1 (surf/lh.sphere.reg)
    surf_fsaverage_sym_method1 = os.path.join(FREESURFER_SUBJ_DIR, 'test_xhemi', 'testvol_lh_fsaverage_sym_lh_method1.mgh')
    command = f"SUBJECTS_DIR={SUBJECTS_DIR} mris_apply_reg --src {surf_nativespace} --trg {surf_fsaverage_sym_method1} --streg {FREESURFER_SUBJ_DIR}/surf/lh.sphere.reg {SUBJECTS_DIR}/fsaverage_sym/surf/lh.sphere.reg"
    subprocess.run(command, shell=True, cwd=os.getcwd(), executable='/bin/bash')

    # resample to fsaverage_sym lh method 2 (surf/lh.fsaverage_sym.sphere.reg)
    surf_fsaverage_sym_method2 = os.path.join(FREESURFER_SUBJ_DIR, 'test_xhemi', 'testvol_lh_fsaverage_sym_lh_method2.mgh')
    command = f"SUBJECTS_DIR={SUBJECTS_DIR} mris_apply_reg --src {surf_nativespace} --trg {surf_fsaverage_sym_method2} --streg {FREESURFER_SUBJ_DIR}/surf/lh.fsaverage_sym.sphere.reg {SUBJECTS_DIR}/fsaverage_sym/surf/lh.sphere.reg"
    subprocess.run(command, shell=True, cwd=os.getcwd(), executable='/bin/bash')
    
    # visualize
    command = f'freeview -f {SUBJECTS_DIR}/fsaverage_sym/surf/lh.inflated:overlay={surf_fsaverage_sym_method1}:overlay={surf_fsaverage_sym_method2}:edgecolor=overlay'
    subprocess.run(command, shell=True, cwd=os.getcwd(), executable='/bin/bash')


def compare_vol2surf_sampling(FREESURFER_SUBJ_DIR, SUBJECTS_DIR, vol):
    # sample lh from vol to surf method 2
    surf_nativespace = os.path.join(FREESURFER_SUBJ_DIR, 'test_xhemi', 'testvol_lh.mgh')
    command = f"SUBJECTS_DIR={SUBJECTS_DIR} mri_vol2surf --src {vol} --out {surf_nativespace} --hemi lh --regheader testsubj --projfrac 0.0"
    subprocess.run(command, shell=True, cwd=os.getcwd(), executable='/bin/bash')

    # sample lh from vol to surf method 2
    surf_nativespace = os.path.join(FREESURFER_SUBJ_DIR, 'test_xhemi', 'testvol_lh.mgh')
    command = f"SUBJECTS_DIR={SUBJECTS_DIR} mri_vol2surf --src {vol} --out {surf_nativespace} --hemi lh --regheader testsubj --projfrac 0.0"
    subprocess.run(command, shell=True, cwd=os.getcwd(), executable='/bin/bash')


if __name__ == '__main__':
    main()