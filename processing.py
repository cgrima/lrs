from . import read
import pandas as pd


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
    df['range0'] = data['DISTANCE_TO_RANGE0']
    
    return df