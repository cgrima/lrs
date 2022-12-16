import numpy as np
import pandas as pd

def lbl_keyword(lbl_filename, keyword):
    """Output a keyword value from a lbl file
    
    ARGUMENTS
    ---------   
    lbl_filename: string
        lbl filename
    keyword: string
        keyword to read
    
    RETURN
    ------
    float
    """
    with open (lbl_filename, "r") as myfile:
        lines = myfile.readlines()

    for line in lines:
        if keyword in line:
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