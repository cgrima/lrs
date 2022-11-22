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
from . import read

class Env:
    """ Class for interacting with data files in the dataset
    """
    def __init__(self, root_path = '../'):
        """ Get various parameters defining the dataset
        """
        self.root_path = root_path
        self.data_path = root_path + 'data/'
        self.code_path = root_path + 'code/'
        self.orig_path = self.data_path + 'orig/'
        self.files = {}
        self.clock_lim = {}
        self.lat_lim = {}
        self.lon_lim = {}
        self.index_files()
        self.read_labels()
        
    def index_files(self):
        """ Index all data files 
        """
        products = os.listdir(self.orig_path)
        # Feel free to append other products no in orig_path
        for product in products:
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
        """
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
                
    def tracks_within_latlon_box(lat_lim, lon_lim, sampling=10e3):
        
        

if __name__ == "__main__":
    # execute only if run as a script
    main()
        
        
def main():
    """ Test Env
    """
    pass
