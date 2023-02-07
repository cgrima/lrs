import numpy as np
import pyproj

def intermediate_latlon(lat_lim, lon_lim, sampling=10e3):
    """ Provide intermediate points along a great circle
    
    ARGUMENTS
    ---------   
    lat_lim: [float, float]
        Latitude of first and last points
    lon_lim: [float, float]
        Longitude of first and last points
    sampling: integer
        space between points [m]
    
    RETURN
    ------
    latlon
    """
    # calculate distance between points
    g = pyproj.Geod(a=1737400, b=1737400) # Moon equatorial and polar radius
    (az12, az21, dist) = g.inv(lon_lim[0], lat_lim[0], lon_lim[1], lat_lim[1])

    # find "npts" points equally spaced by "sampling" meters
    npts = dist/sampling
    del_s = sampling
    r = g.fwd_intermediate(lon_lim[0], lat_lim[0], az12, npts=npts, del_s=del_s)

    # Output structure
    lon360s = [lon + 360 if lon < 0 else lon for lon in r.lons]
    lats = [lat for lat in r.lats]
    #latlons = [[r.lats[i], lon360s[i]] for i in np.arange(r.npts)]

    # Append first and last coordinates of the track
    lon360s.insert(0, lon_lim[0])
    lats.insert(0, lat_lim[0])
    lon360s.append(lon_lim[1])
    lats.append(lat_lim[1])
    
    #latlons.insert(0, (lat_lim[0], lon_lim[0]))
    #latlons.append((lat_lim[1], lon_lim[1]))
    
    return {'lats':lats, 'lons':lon360s}