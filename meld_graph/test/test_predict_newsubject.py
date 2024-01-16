#### tests for scripts/new_patient_pipeline.py ####
# this test used the patient MELD_TEST_3T_FCD_0011
# it test  : 
# - the prediction on new subject using meld_graph.predict_newsubject
# - the prediction registration using scripts.manage_results.move_predictions_to_mgh.py
# - the prediction registration back to native MRI using scripts.manage_results.register_back_to_xhemi.sh
# - the creation of the MELD pdf reports
# It checks outputs exists and compare the prediction with the expected one.

import subprocess
import os
import pytest
import h5py
import numpy as np
import nibabel as nb
from meld_graph.paths import MELD_DATA_PATH
from meld_graph.download_data import get_test_data

def get_data_parameters():
    data_parameters = {
        "subject": "sub-test0001",
        "harmo code" :"TEST",
        "experiment_folder":"output/classifier_outputs", 
        "expected_prediction_hdf5_file" : os.path.join("results", "predictions_ensemble_iteration_expected.hdf5"),
        "prediction_hdf5_file" : os.path.join("results", "predictions_ensemble_iteration.hdf5"),
        "expected_prediction_nii_file" : "{}.prediction_expected.nii",
        "prediction_nii_file" : "{}.prediction.nii.gz"
    }
    return data_parameters


def load_prediction(subject,hdf5):
    results={}
    with h5py.File(hdf5, "r") as f:
        for hemi in ['lh','rh']:
            results[hemi] = f[subject][hemi]['prediction_clustered'][:]
    return results

@pytest.mark.slow
def test_predict_newsubject():
    # ensure test input data is present
    get_test_data()
    
    # initiate parameter
    data_parameters = get_data_parameters()
    subject = data_parameters['subject']
    # call script run_script_prediction.py
    print("calling")
    dir_path = os.path.dirname(os.path.realpath(__file__))
    script_path = os.path.abspath(os.path.join(dir_path, "../../scripts/new_patient_pipeline/run_script_prediction.py"))
    print(script_path)
    subprocess.run(
                [
                    "python",
                    script_path,
                    "-id",
                    data_parameters['subject'],
                    "-harmo_code",
                    data_parameters['harmo code'],
                    "--debug_mode"
                ]
            )

    # check if the expected folder structure was created_ex
    path_prediction_subject = os.path.join(MELD_DATA_PATH, 'output', 'predictions_reports', subject, 'predictions')
    assert os.path.isdir(path_prediction_subject)
    
    ## compare results prediction with expected one
    # compare prediction hdf5 
    exp_path = os.path.join(MELD_DATA_PATH, data_parameters['experiment_folder'])    
    prediction = load_prediction(subject, os.path.join(exp_path, data_parameters['prediction_hdf5_file']))
    expected_prediction = load_prediction(subject,os.path.join(exp_path, data_parameters['expected_prediction_hdf5_file']))
    for hemi in ['lh','rh']:
        diff_sum = (np.abs(prediction[hemi] - expected_prediction[hemi])).sum()
        print(f'Test HDF5 results: Number of vertices different with expectation for {hemi} hemi : {diff_sum}')
        assert diff_sum <= 350

    # compare prediction on mri native
    for hemi in ['lh','rh']:
        prediction_nii = nb.load(os.path.join(path_prediction_subject,data_parameters['prediction_nii_file'].format(hemi))).get_fdata()
        expected_prediction_nii = nb.load(os.path.join(path_prediction_subject,data_parameters['expected_prediction_nii_file'].format(hemi))).get_fdata()
        diff_sum = (np.abs(prediction_nii - expected_prediction_nii)).sum()
        print(f'Test nifti results: Number of vertices different with expectation for {hemi} hemi : {diff_sum}')
        assert diff_sum <= 350
 
