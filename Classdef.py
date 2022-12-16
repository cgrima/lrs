#!/usr/bin/env python3
# Tools to explore LRS data

"""
LRS = lrs.Env()
LRS.orbit_data(orbitname)

"""

import os
import sys
import glob
import logging
import numpy as np
import pandas as pd
from shapely.geometry import Point, Polygon
from . import read, tools

class Env:
    """ Class for interacting with data files in the dataset
    """
    def __init__(self, root_path = '../'):
        """ Get various parameters defining the dataset
        """
        self.root_path = root_path
        self.data_path = root_path + 'data/'
        self.code_path = root_path + 'code/'
        self.orig_path = self.data_path + 'lrs/orig/'
        self.xtra_path = self.data_path + 'lrs/xtra/'
        self.files = {}
        self.clock_lim = {}
        self.lat_lim = {}
        self.lon_lim = {}
        self.index_files()
        self.read_labels()
        
    def index_files(self):
        """ Index all data files 
        """
        self.products = os.listdir(self.orig_path)
        # Feel free to append other products no in orig_path
        for product in self.products:
            self.files[product] = {}
            product_path = self.orig_path + product + '/'
            for day in os.listdir(product_path):
                filenames = glob.glob(product_path + day + '/data/*.*')
                for filename in filenames:
                    name = filename.split('_')[-1].split('.')[0]
                    if name not in self.files[product].keys():
                        self.files[product][name] = {}
                        files = glob.glob(product_path + day + '/data/*' 
                                          + name + '*.*')
                        self.files[product][name] = files

    def read_labels(self):
        """ Read and store in the Class some parameters from the label files
        """
        for product in self.files.keys():
            self.clock_lim[product] = {}
            self.lat_lim[product] = {}
            self.lon_lim[product] = {}
            for name in self.files[product].keys():
                lbl_filenames = [file for file in self.files[product][name] 
                if '.lbl' in file]
                lbl_filename = lbl_filenames[0]
                # Clock
                lim1 = read.lbl_keyword(lbl_filename,
                'SPACECRAFT_CLOCK_START_COUNT')
                lim2 = read.lbl_keyword(lbl_filename,
                'SPACECRAFT_CLOCK_STOP_COUNT')
                self.clock_lim[product][name] = [lim1, lim2]
                # Latitude
                lim1 = read.lbl_keyword(lbl_filename,
                'START_SUB_SPACECRAFT_LATITUDE')
                lim2 = read.lbl_keyword(lbl_filename,
                'STOP_SUB_SPACECRAFT_LATITUDE')
                self.lat_lim[product][name] = [lim1, lim2]
                # Longitude
                lim1 = read.lbl_keyword(lbl_filename,
                'START_SUB_SPACECRAFT_LONGITUDE')
                lim2 = read.lbl_keyword(lbl_filename,
                'STOP_SUB_SPACECRAFT_LONGITUDE')
                self.lon_lim[product][name] = [lim1, lim2]
                
    def product_match(self, product):
        """ Return the full name of a product from a substring
        
        ARGUMENTS
        ---------
        product: string
            Substring of the product
        
        RETURN
        ------
        string
        """
        res = [i for i in self.products if product in i]
        
        if len(res) > 1:
            print('Several products match this substring:')
            for i in res:
                print('  ' + i)
        else:
            return res[0]
                
    def orig_data(self, product, name):
        """ Read orig data
        
        ARGUMENT
        --------
        product: string
            product full name or substring (e.g., sar05)
        name: string
            file identifier (e.g., '20071221033918')
            
        RETURN
        ------
        
        """
        product = self.product_match(product)
        files = self.files[product][name]
        lbl_filename = [file for file in files if '.lbl' in file][0]
        img_filename = [file for file in files if '.img' in file][0]
        aux, img = read.img(img_filename, lbl_filename)
        out = aux.to_dict(orient='list')
        out.update({'IMG':img})
        
        return out#.update({'DATA':img})

    def tracks_intersecting_latlon_box(self, boxlats, boxlons, sampling=10e3,
                                       download=False):
        """ Return identifiers of tracks crossing a box bounded by latitudes
        and longitudes. Uses great circle interpolation between between end 
        points of each tracks.
        
        ARGUMENTS
        ---------   
        boxlats: [float, float]
            Box first and last longitudes
        boxlons: [float, float]
            Box first and last longitudes
        sampling: integer
            space between points interpolated between tracks end points [m]
        download: binary
            Whether to download the corresponding files into the local 
            hierarchy
    
        RETURN
        ------
        tuple{'lats', 'lons'}
        """
        # Create a square
        box = [(boxlons[0], boxlats[0]), 
               (boxlons[0], boxlats[1]), 
               (boxlons[1], boxlats[1]), 
               (boxlons[1], boxlats[0])
               ]
        poly = Polygon(box)

        products = self.products
        out = []
        for product in products:
            for track in self.files[product].keys():
                coord = tools.intermediate_latlon(self.lat_lim[product][track],
                                                  self.lon_lim[product][track],
                                                  sampling=sampling)
                # Test if a point is within the latlon box
                inbox = [Point(coord['lons'][j], coord['lats'][j]).within(poly) 
                         for j in np.arange(len(coord['lats']))]
                if True in inbox:
                    out = out + [[product, track]]
                    
        if download:
            for track in out:
                product = track[0]
                name = track[1]
                print(f'Downloading {track}')
                
                mkdir_cmd = f'mkdir -p {self.orig_path}{product}/{name[0:8]}'
                os.system(mkdir_cmd)
                
                lftp_cmd = f'lftp -c "open https://data.darts.isas.jaxa.jp/pub/pds3/{product}/{name[0:8]}/;' \
                + f'mirror -c -P 10 --only-missing -I \'*{name}*\' ' \
                + f'data {self.orig_path}{product}/{name[0:8]}/" '

                os.system(lftp_cmd)
        
        return out
        
        

if __name__ == "__main__":
    # execute only if run as a script
    main()

        
def main():
    """ Test Env
    """
    pass
