import numpy as np
import pandas as pd
import subradar as sr
from obspy.core import AttribDict
from obspy.core import Stats
from obspy.core import Trace, Stream
from obspy.io.segy.segy import SEGYBinaryFileHeader
from obspy.io.segy.segy import SEGYTraceHeader


def anc(data, **kwargs):
    """ Create ancilliary data from the headers in the orignal data
    
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
    
    # surface estimate
    y_size = np.shape(img)[1]
    ymax = [np.argmax(img[:,i]) for i in np.arange(y_size)]
    y_estimate = np.mean(ymax)
    
    if method == 'mouginot2010':
        img_for_detection = 10**(img/20)
        y0 = np.zeros(np.shape(img)[1])+y_estimate
        winsize = 300
        
    if method == 'grima2012':
        img_for_detection = 10**(img/20)
        y0 = np.zeros(np.shape(img)[1])+y_estimate
        winsize = 300
        
    y = sr.surface.detector(img_for_detection, axis=1, 
                            y0=y0, winsize=winsize, method=method)
    
    y = np.flip(y) #surface.detector returns y backwards?
    y = [int(val) for val in y]
    
    pdb = [img[val, i] for i, val in enumerate(y)]
    amp = [10**(val/20) for val in pdb]
    
    df = pd.DataFrame({'y':y, 'pdb':pdb, 'amp':amp})
    
    return df


def sgy(data, **kwargs):
    ''' Convert data to segy
    '''

    out = Stream()                      # Make a new Stream object, basically an empty list-like thing.
    rdg = np.float32(data['IMG_pdb'])
    rdg = np.flip( np.rot90(rdg), axis=0)
    for i, t in enumerate(rdg):                # Loop over all trace-like things in the similarity array.
        header = {'delta':0.05/1e6, 
                  'bin':i,
                  'latitude':data['SUB_SPACECRAFT_LATITUDE'][i],
                  'longitude':data['SUB_SPACECRAFT_LONGITUDE'][i],
                  'altitude':data['SPACECRAFT_ALTITUDE'][i],
                 }          # Make a header for the trace; ObsPy needs this.
        #for key in data.keys:
        #    header.update({key:data[key][i]})
        trace = Trace(t, header=header) # Make the ObsPy Trace with the data and the header.
        out.append(trace)               # Append the Trace to the Stream.
        
    # Header
    header = """JAXA/Lunar Radar Sounder (LRS)
    Algorithm: https://github.com/cgrima/lrs/blob/main/processing.py.
    dt = 0.05 s. (along-track sampling)
    dz =  = 25 m. in void (Range Resolution)""".encode('utf-8')
    
    out.stats = Stats(dict(textual_file_header=header))
    
    return out