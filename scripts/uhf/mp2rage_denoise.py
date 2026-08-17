
import os
import nibabel as nib
import numpy as np
from copy import deepcopy

def mp2rage_robust_combination(uni_path,
                               inv1_path,
                               inv2_path,
                               output_path,
                               beta,
                               overwrite = True):
    """
    This is a version of the "robust" denoise MP2RAGE calculation described
    by O'Brien et al. (2014), MATLAB implementations by Jose Marques 
    (https://github.com/JosePMarques/MP2RAGE-related-scripts) and Benoit Beranger
    (https://github.com/benoitberanger/mp2rage, ported to python by Marc Pabst 
    (https://github.com/marcpabst/mp2rage-denoise/), further reference is the
    laynii implementation (https://github.com/layerfMRI/LAYNII/blob/master/src/LN_MP2RAGE_DNOISE.cpp)
    Adapted (keeping the original nifti header, using a beta instead 
    of noise level estimation and accounting for Siemens 12bit int values 
    Args:
        filename_uni (str): Path to the uniform T1-image (UNI). Can be 
                            either a float image in [-0.5, 0.5] or a Siemens 12bit
                                integer image in [0, 4095].
        filename_inv1 (str): Path to the first inversion image (INV1).
        filename_inv2 (str): Path to the second inversion image (INV2).
                             INV1 and INV2 are expected on the Siemens 12bit 
                             integer scale [0, 4095].
        filename_output (str, optional): Path to output image.
        beta (float, optional): Regularisation parameter, default is 0.1.
        overwrite (bool, optional): If False, check whether output file already exists and if so,
                                    quit without regenerating and overwriting the file.
    Returns:
        str: Path to the output image.
    """
    MAX12BIT = 4095.0

    if os.path.isfile(output_path) and not overwrite:
        return output_path

    # define relevant functions
    mp2rage_robustfunc  =  lambda inv1, inv2, beta: (inv1.conj() * inv2 - beta) / (np.square(inv1) + np.square(inv2) + 2*beta)

    rootsquares_pos  = lambda a,b,c: (-b+np.sqrt(np.square(b) -4 *a*c))/(2*a)
    rootsquares_neg  = lambda a,b,c: (-b-np.sqrt(np.square(b) -4 *a*c))/(2*a)

    # load data
    image_uni  = nib.load(uni_path)
    image_inv1 = nib.load(inv1_path)
    image_inv2 = nib.load(inv2_path)

    image_uni_fdata = image_uni.get_fdata()
    image_inv1_fdata = image_inv1.get_fdata()
    image_inv2_fdata  = image_inv2.get_fdata()

    # The algorithm needs the UNI in the range [-0.5, 0.5]. Data with negative values
    # is assumed to be in that range already; positive-only data is either Siemens
    # 12bit integers [0, 4095] or a [0, 1] normalisation, told apart by the maximum.
    if np.min(image_uni_fdata) >= 0.0:
        if np.max(image_uni_fdata) > 1.0:
            image_uni_fdata = image_uni_fdata / MAX12BIT - 0.5
        else:
            image_uni_fdata = image_uni_fdata - 0.5

    # correct polarity for INV1
    image_inv1_fdata = np.sign(image_uni_fdata) * image_inv1_fdata

    # MP2RAGEimg is a phase sensitive coil combination.. some more maths has to
    # be performed to get a better INV1 estimate which here is done by assuming
    # both INV2 is closer to a real phase sensitive combination
    inv1_pos = rootsquares_pos(-image_uni_fdata, image_inv2_fdata, -np.square(image_inv2_fdata) * image_uni_fdata)
    inv1_neg = rootsquares_neg(-image_uni_fdata, image_inv2_fdata, -np.square(image_inv2_fdata) * image_uni_fdata)

    image_inv1_final_fdata = deepcopy(image_inv1_fdata)

    image_inv1_final_fdata[np.abs(image_inv1_fdata - inv1_pos) >  np.abs(image_inv1_fdata - inv1_neg)] = inv1_neg[np.abs(image_inv1_fdata - inv1_pos) >  np.abs(image_inv1_fdata - inv1_neg)]
    image_inv1_final_fdata[np.abs(image_inv1_fdata - inv1_pos) <= np.abs(image_inv1_fdata - inv1_neg)] = inv1_pos[np.abs(image_inv1_fdata - inv1_pos) <= np.abs(image_inv1_fdata - inv1_neg)]

    beta = beta * MAX12BIT
    output = mp2rage_robustfunc(image_inv1_final_fdata, image_inv2_fdata, beta)

    image_output = nib.Nifti1Image(output, image_uni.affine, image_uni.header)
    # the combination is a small float in [-0.5, 0.5]; without this it would inherit
    # the (typically integer) dtype of the UNI image and be written via scl_slope/inter
    image_output.set_data_dtype(np.float32)

    nib.save(image_output, output_path)

    return output_path

if __name__ == "__main__":
    import argparse
    argparser = argparse.ArgumentParser(description="Denoise MP2RAGE UNI image using INV1 and INV2 images")
    argparser.add_argument("-uni", "--uni", type=str, required=True, help="Path to the MP2RAGE UNI image")
    argparser.add_argument("-inv1", "--inv1", type=str, required=True, help="Path to the MP2RAGE INV1 image")
    argparser.add_argument("-inv2", "--inv2", type=str, required=True, help="Path to the MP2RAGE INV2 image")
    argparser.add_argument("-out", "--out", type=str, required=True, help="Path to the output denoised UNI image")
    argparser.add_argument("-b", "--beta", type=float, default=0.1, help="Regularisation parameter beta (default: 0.1)")
    argparser.add_argument("--overwrite", action='store_true', help="Whether to overwrite existing output file")
    args = argparser.parse_args()

    denoised_image_path = mp2rage_robust_combination(
        args.uni,
        args.inv1,
        args.inv2,
        args.out,
        args.beta,
        args.overwrite
    )