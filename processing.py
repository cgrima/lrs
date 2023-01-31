import numpy as np
import pandas as pd
import subradar as sr
from . import read


def aux(data, **kwargs):
    """ Create auxilliary data from the headers in the orignal data
    
    ARGUMENTS
    ---------
    data: dict
        Classdef.Env.orig_data()
    """
    df = pd.DataFrame()
    dates = data['OBSERVATION_TIME']
    df['date'] = [str(date)[2:-1] for date in dates]
    df['time'] = [''.join(''.join(''.join(
                  d.split('.')[0].split('T')).split('-')).split(':')) 
                  for d in df['date']]
    df['delay'] = data['DELAY']
    df['latitude'] = data['SUB_SPACECRAFT_LATITUDE']
    df['longitude'] = data['SUB_SPACECRAFT_LONGITUDE']
    df['altitude'] = data['SPACECRAFT_ALTITUDE']
    if 'DISTANCE_TO_RANGE0' in data.keys():
        df['range0'] = data['DISTANCE_TO_RANGE0']
    else:
        df['range0'] = np.zeros(len(data['OBSERVATION_TIME']))
    
    return df


def srf(data, method='mouginot2010', **kwargs):
    """ Create surface data from the headers in the orignal data
    
    ARGUMENTS
    ---------
    data: dict
        Classdef.Env.orig_data()
    method: string
        Method to pick the surface (passed to subradar.surface.pick.detector)
    kwargs: tuple
        arguments from subradar.surface.detector
        
    RETURN
    ------
    Dictionary of coordinate (y), power in dB (pdb), and linear amplitude (amp)
    """
    df = pd.DataFrame()
    
    # Data
    img = np.array(data['IMG_pdb'])
    
    if method == 'mouginot2010':
        img_for_detection = 10**(img/20)
        y0 = np.zeros(np.shape(img)[1])+200
        winsize = 300
        
    if method == 'grima2012':
        img_for_detection = 10**(img/20)
        y0 = np.zeros(np.shape(img)[1])+200
        winsize = 300
        
    y = sr.surface.detector(img_for_detection, axis=1, 
                            y0=y0, winsize=winsize, method=method)
    
    y = np.flip(y) #surface.detector returns y backwards?
    y = [int(val) for val in y]
    
    pdb = [img[val, i] for i, val in enumerate(y)]
    amp = [10**(val/20) for val in pdb]
    
    df = pd.DataFrame({'y':y, 'pdb':pdb, 'amp':amp})
    
    return df