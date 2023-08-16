import numpy as np
import pandas as pd
import subradar as sr
from obspy.core import AttribDict, Stats, Trace, Stream
from obspy.io.segy.segy import SEGYBinaryFileHeader, SEGYTraceHeader
import scipy.io
from pyproj import CRS, Transformer
from . import read



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
    df['pmax'] = data['Pmax']
    df['pmin'] = data['Pmin']
    if 'DISTANCE_TO_RANGE0' in data.keys():
        df['range0'] = data['DISTANCE_TO_RANGE0']
    else:
        df['range0'] = np.zeros(len(data['OBSERVATION_TIME']))
        
    # Get data from kernels
    kernels = read.spice_kernels(list(df['date']))
    for key in kernels.keys():
        df[key] = kernels[key]
        
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
    """ Convert data to segy
    """

    # Transfomer to convert lat/lon to XY polar
    crs_lonlat = '+proj=longlat +R=1737400 +no_defs'
    crs_stereo = '+proj=stere +lat_0=-90 +lon_0=0 +k=1 +x_0=0 +y_0=0 +R=1737400 +units=m +no_defs +type=crs'
    transformer = Transformer.from_crs(CRS.from_string(crs_lonlat), 
                                        CRS.from_proj4(crs_stereo))
    
    # Make a new Stream object, basically an empty list-like thing.
    out = Stream()
    
    # Rotate radargram for processing
    rdg = np.float32(data['IMG_pdb'])
    rdg = np.flip( np.rot90(rdg), axis=0)
    
    # Loop over all trace-like things in the similarity array.
    for i, t in enumerate(rdg): 
        x, y = transformer.transform(data['SUB_SPACECRAFT_LONGITUDE'][i], 
                                     data['SUB_SPACECRAFT_LATITUDE'][i])
        
        trace = Trace(t) # Make the ObsPy Trace with the data 
        # Add required data.
        trace.stats.delta = 0.0015#0.05/1e6
        trace.stats.starttime = 0  # Not strictly required.
        # Add yet more to the header (optional).
        trace.stats.segy = {'trace_header': SEGYTraceHeader()}
        trace.stats.segy.trace_header.trace_sequence_number_within_line = i + 1
        trace.stats.segy.trace_header.trace_sequence_number_within_segy_file = i + 1
        trace.stats.segy.trace_header.ensemble_number = i + 1
        trace.stats.segy.trace_header.receiver_group_elevation = int(data['SPACECRAFT_ALTITUDE'][i]*1e3)
        trace.stats.segy.trace_header.ensemble_number = i + 1
        trace.stats.segy.trace_header.scalar_to_be_applied_to_all_coordinates = 1
        trace.stats.segy.trace_header.source_coordinate_x = int(x)
        trace.stats.segy.trace_header.source_coordinate_y = int(y)
        trace.stats.segy.trace_header.group_coordinate_x = int(x) # same as source positions
        trace.stats.segy.trace_header.group_coordinate_y = int(y) # same as source positions
        trace.stats.segy.trace_header.coordinate_units = 1 # 1 = length (meters or feet)
        trace.stats.segy.trace_header.trace_value_measurement_unit = 1 # 1 = length (meters or feet)
        trace.stats.segy.trace_header.transduction_units = 1 # 1 = length (meters or feet)
        trace.stats.segy.trace_header.source_measurement_unit = 1 # 1 = length (meters or feet)
        trace.stats.segy.trace_header.sample_interval_in_ms_for_this_trace = 1.6 # ms*10000
        #trace.stats.segy.number_of_samples_in_this_trace = 0 # Done automatically by ObsPy
        trace.stats.segy.trace_header.sample_interval_in_ms_for_this_trace = 50
        trace.stats.segy.trace_header.x_coordinate_of_ensemble_position_of_this_trace = int(x) # Maybe same as source positions
        trace.stats.segy.trace_header.y_coordinate_of_ensemble_position_of_this_trace = int(y) # Maybe same as source positions
        
        out.append(trace)               # Append the Trace to the Stream.
        
    # Header
    header = f"""JAXA/Lunar Radar Sounder (LRS)
    Algorithm: https://github.com/cgrima/lrs/blob/main/processing.py.
    dt = 0.05 s. (along-track sampling)
    dz = 24 m. in void (Range Resolution)
    Sample interval within a trace = 160 nanoseconds
    xy coordinates are derived from southern polar stereographic projection with radius = 1737400 m""".encode('utf-8')
    
    out.stats = Stats(dict(textual_file_header=header))
    
    return out
