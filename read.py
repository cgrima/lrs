import numpy as np
import pandas as pd
import spiceypy as spice
import os
import logging


def lbl_keyword(lbl_filename, keyword, fullline=False):
    """Output a keyword value from a lbl file
    
    ARGUMENTS
    ---------   
    lbl_filename: string
        lbl filename
    keyword: string
        keyword to read
    fullline: Binary
        If True, will output the first entire line where a string match is found
    
    RETURN
    ------
    float
    """
    with open (lbl_filename, "r") as myfile:
        lines = myfile.readlines()

    for line in lines:
        if keyword in line:
            if fullline:
                value = line
            else:
                value = "".join(line.split()).split('=')[-1].replace('"', '')
    
    # Set correct output type
    try:
        if '.' in value:
            return float(value)
        else:
            return int(value)
    except  ValueError:
        return value

    
def img(img_filename, lbl_filename):
    """Read a binary LRS file
    
    ARGUMENTS
    ---------
    img_filename: string
        image filename   
    lbl_filename: string
        lbl filename
    
    RETURN
    ------
    header, img
    """
    
    #---------
    # METADATA
    #---------
    
    DATA_SET_ID = lbl_keyword(lbl_filename, 'DATA_SET_ID')
    RECORD_BYTES = lbl_keyword(lbl_filename, 'RECORD_BYTES')
    FILE_RECORDS = lbl_keyword(lbl_filename, 'FILE_RECORDS')
    IMG_LINES = lbl_keyword(lbl_filename, 'LINES')
    TOTAL_BYTES = RECORD_BYTES*FILE_RECORDS
    IMG_OFFSET = (FILE_RECORDS - IMG_LINES)*RECORD_BYTES
    
    #-------
    # HEADER
    #-------
    
    if (DATA_SET_ID == 'SLN-L-LRS-5-SNDR-SS-SAR05-POWER-V1.0') | \
       (DATA_SET_ID == 'SLN-L-LRS-5-SNDR-SS-SAR10-POWER-V1.0') | \
       (DATA_SET_ID == 'SLN-L-LRS-5-SNDR-SS-SAR40-POWER-V1.0'):
        
        DTYPE_LAYOUT = np.dtype([("OBSERVATION_TIME", 'S23'),
                                 ("DELAY", '<f4'),
                                 ("START_STEP", '<u2'),
                                 ("SUB_SPACECRAFT_LATITUDE", '<f4'),
                                 ("SUB_SPACECRAFT_LONGITUDE", '<f4'),
                                 ("SPACECRAFT_ALTITUDE", '<f4'),
                                 ("DISTANCE_TO_RANGE0", '<f4'),
                                 ("TI", 'S10'),
                                ])
    elif (DATA_SET_ID == 'SLN-L-LRS-5-SNDR-SS-HIGH-V2.0'):
        
        DTYPE_LAYOUT = np.dtype([("OBSERVATION_TIME", 'S23'),
                                 ("DELAY", '<f4'),
                                 ("START_STEP", '<u2'),
                                 ("SUB_SPACECRAFT_LATITUDE", '<f4'),
                                 ("SUB_SPACECRAFT_LONGITUDE", '<f4'),
                                 ("SPACECRAFT_ALTITUDE", '<f4'),
                                ])
        
        
    header = np.fromfile(img_filename, dtype=DTYPE_LAYOUT, count=RECORD_BYTES)
    header = pd.DataFrame(header)

    #------
    # IMAGE
    #------

    img = np.fromfile(img_filename, dtype='B', offset=IMG_OFFSET)
    img = img.reshape(IMG_LINES, RECORD_BYTES)
    
    return header, img


def spice_kernels(UTCs, kernels_path = ['..', 'data', 'orig', 'kernels']):
    """Extract data from Kaguya SPICE kernels at a given time.
    Kernel can be downloaded at https://data.darts.isas.jaxa.jp/pub/spice/SELENE/
    and needs to be added in ../data/orig/kernels
    
    ARGUMENTS
    ---------
    UTCs: string or string array
        UTC time time in the format '2008-05-18T14:56:11.776'
    
    RETURN
    ------
    S/C position (x, y, z), velocity (vx, vy, vz) and attitude (roll, pitch, yaw) parameters
    """    
    # Load Kernels
    # ------------
    
    try:
        spice.furnsh(os.path.join(*kernels_path, 'lsk', 'naif0009.tls'))
        spice.furnsh(os.path.join(*kernels_path, 'ck', 'SEL_M_ALL_S_V03.BC'))
        spice.furnsh(os.path.join(*kernels_path, 'spk', 'SEL_M_071020_090610_SGMH_02.BSP'))
        spice.furnsh(os.path.join(*kernels_path, 'fk', 'SEL_V01.TF'))
        spice.furnsh(os.path.join(*kernels_path, 'fk', 'moon_080317.tf'))
        spice.furnsh(os.path.join(*kernels_path, 'pck', 'moon_pa_de421_1900-2050.bpc'))
        spice.furnsh(os.path.join(*kernels_path, 'pck', 'pck00010.tpc'))
        spice.furnsh(os.path.join(*kernels_path, 'sclk', 'SEL_M_V01.TSC'))
    except:
        logging.warning('Kernel files were not found')
        return None

    # Data adjustments
    # ----------------
    
    # Convert UTCs to a list if not (ao that a one element UTCS can be processed)
    if type(UTCs) is not list:
        UTCs = [UTCs]
    
    # Convert UTC to various time formats
    ETs = [spice.utc2et(UTC) for UTC in UTCs] 
    SCLKs = [spice.sce2c(-131, ET) for ET in ETs]

    # Get S/C SPICE positions and velocity
    # ------------------------------

    stargs, lightTimes = spice.spkezr('SELENE', ETs, 'J2000', 'NONE', 'MOON')

    x = [starg[0] for starg in stargs]
    y = [starg[1] for starg in stargs]
    z = [starg[2] for starg in stargs]
    vx = [starg[3] for starg in stargs]
    vy = [starg[4] for starg in stargs]
    vz = [starg[5] for starg in stargs]

    # Get S/C SPICE pointing (attitude)
    # ---------------------------------

    # Rotation Matrices
    try:
        rotMats = [spice.ckgp(-131000, SCLK, 10, 'MOON_ME')[0] for SCLK in SCLKs]

        # Get the body-fixed frame transformation matrix from the reference frame
        ref2bodyMats = [spice.pxform('MOON_ME', 'SELENE_M_SPACECRAFT', ET) for ET in ETs]

        # Apply the inverse of the body-fixed frame transformation to get the attitude in the body-fixed frame
        body_fixed_attitudes = [np.matmul(np.linalg.inv(ref2bodyMats[i]), rotMats[i]) for i in np.arange(len(ETs))]

        # Extract the roll, pitch, and yaw angles from the body-fixed attitude matrix
        attitudes = [spice.m2eul(body_fixed_attitude, 3, 2, 1) for body_fixed_attitude in body_fixed_attitudes]

        roll = [np.rad2deg(euler[0]) for euler in attitudes]
        pitch = [np.rad2deg(euler[1]) for euler in attitudes]
        yaw = [np.rad2deg(euler[2]) for euler in attitudes]
        
    except:
        roll = list(np.array(x)*0+555)
        pitch = list(np.array(x)*0+555)
        yaw = list(np.array(x)*0+555)

    # Clean up the kernels
    # --------------------

    spice.kclear()
    
    return {'x_moon':x, 'y_moon':y, 'z_moon':z, 
            'vx_moon':vx, 'vy_moon':vy, 'vz_moon':vz,
            'roll':roll, 'pitch':pitch, 'yaw':yaw}