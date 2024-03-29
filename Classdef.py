#!/usr/bin/env python3
# Tools to explore LRS data

"""
LRS = lrs.Env()
LRS.orbit_data(orbitname)

"""

import os
import sys
import glob
import copy
import logging
import numpy as np
import pandas as pd
import requests
import urllib
import pyproj
from datetime import datetime
from shapely.geometry import Point, Polygon
from scipy.interpolate import UnivariateSpline
from joblib import Parallel, delayed
from pyproj import CRS
from pyproj import Transformer
import matplotlib.pyplot as plt
from . import read, tools, processing


class Env:
    """ Class for interacting with data files in the dataset
    """
    def __init__(self, root_path = os.path.join('..', '')):
        """ Get various parameters defining the dataset
        """
        self.remote_host = 'https://data.darts.isas.jaxa.jp/pub/pds3/'
        self.root_path = root_path
        self.code_path = os.path.join(root_path, 'code', '')#root_path + 'code/'
        self.data_path = os.path.join(root_path, 'data', '')#root_path + 'data/'
        self.orig_path = os.path.join(self.data_path, 'orig', 'lrs', '')#self.data_path + 'orig/lrs/'
        self.xtra_path = os.path.join(self.data_path, 'xtra', 'lrs', '')#self.data_path + 'xtra/lrs/'
        self.files = {}
        self.clock_lim = {}
        self.epoch_lim = {}
        self.lat_lim = {}
        self.lon_lim = {}
        self.initialize_hierarchy()
        self.products = self.index_products()
        self.index_files()
        self.read_labels()
        
    def initialize_hierarchy(self):
        paths = [self.data_path,
                 self.orig_path,
                 self.xtra_path
                ]
        
        for path in paths:
            if not glob.glob(path):
                os.makedirs(path)
                logging.info(path + ' CREATED')
        
        
    def index_products(self, path=False):
        """List available products
        """
        out = os.listdir(self.orig_path)
        
        for xtra in os.listdir(self.xtra_path):
            products = os.listdir(os.path.join(self.xtra_path, xtra))
            out.extend(products)
        
        out = list(set(out)) # unique products
        return out
        
        
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
            logging.warning('Several products match this substring:')
            for i in res:
                print(i)
        else:
            return res[0]

        
    def download(self, product, name, typ='lbl', delete=False, delete_only=False):
        """ Download original data for a given product and name
        
        ARGUMENTS
        ---------
        product: string
            product full name or substring (e.g., sar05)
        name: string
            file identifier (e.g., '20071221033918')
        typ: string
            File extension (lbl or img)
        delete: binary
            whether to delete existing local file
        delete_only: string
            delete the local file
        
        RETURN
        ------
        0 = File has not been downloaded
        1 = File has been downloaded
        2 = File has been localy deleted
        
        """
        #filename = 'LRS_' + product.split('-')[6].upper() + 'KM_' + name + '.' + typ6 
        filename = self.filename_root(product, name) + '.' + typ
        #relative_path = os.path.join(product, name[:8], 'data')
        #remote_file = os.path.join(self.remote_host, relative_path, filename)
        remote_file = urllib.parse.urljoin(self.remote_host, product + '/' + name[:8] + '/data' + '/' + filename)
        local_file = os.path.join(self.orig_path, product, name[:8], 'data', filename)
        
        if not glob.glob(local_file) or delete:
            # Download file
            os.makedirs(os.path.join(self.orig_path, product, name[:8], 'data'), exist_ok=True)
            response = requests.get(remote_file)
            if response.status_code == 200:
                open(local_file, "wb").write(response.content)
                out_code = 1
                logging.info(f' [{out_code}] {local_file} DOWNLOADED')
            else:
                logging.info(' ' + remote_file + f' DOES NOT EXIST (Error {response.status_code})')
        elif delete_only == True:
            # Erase local file only
            os.remove(local_file)
            out_code = 2
            logging.info(f' [{out_code}] {local_file} DELETED')
        else:
            # Do not do anything
            out_code = 0
            logging.info(f' [{out_code}] {local_file} EXISTS (NOT DOWNLOADED)')
            
        return out_code
    
    
    def filename_root(self, product, name):
        """ output the filename of a product track following the JAXA convention
        """
        if product == 'sln-l-lrs-5-sndr-ss-high-v2.0':
            middle_name = 'SWH_RV20'
        if product == 'sln-l-lrs-5-sndr-ss-sar05-power-v1.0':
            middle_name = 'SAR05KM'
        if product == 'sln-l-lrs-5-sndr-ss-sar10-power-v1.0':
            middle_name = 'SAR10KM'
        if product == 'sln-l-lrs-5-sndr-ss-sar40-power-v1.0':
            middle_name = 'SAR40KM'
        if product == 'sln-l-lrs-5-sndr-ss-nfoc-power-v1.0':
            middle_name = 'NFOC'
            
        filename = '_'.join(['LRS', middle_name, name])
        return filename
    
        
    def index_files(self):
        """ Index all data files 
        """
        # Logging Header
        cols = ['---', 'Product', 'lbl', 'img', 'anc', 'srf', 'sim']
        logging.info(f' {cols[1]:^37} {cols[2]:>7} {cols[3]:>7} {cols[4]:>7} {cols[5]:>7} {cols[6]:>7}')
        logging.info(f' {cols[0]:^37} {cols[0]:>7} {cols[0]:>7} {cols[0]:>7} {cols[0]:>7} {cols[0]:>7}')

        # list products
        for product in self.products:
            # Indicate below what folders need to be indexed
            index_paths = [os.path.join(self.orig_path, product),
                           os.path.join(self.xtra_path, 'anc', product),
                           os.path.join(self.xtra_path, 'srf', product),
                           os.path.join(self.xtra_path, 'sim', product),]
            
            self.files[product] = {}
            for path in index_paths:
                if os.path.exists(path):
                    for day in os.listdir(path):
                        search_path = os.path.join(path, day, 'data', '*.*')
                        filenames = glob.glob(search_path)
                        #filenames = glob.glob(path + '/' + day + '/data/*.*')
                        for filename in filenames:
                            name = [i for i in filename.split('_') 
                                    if '200' in i][-1][:14]
                            #name = filename.split('_')[-1][:14]
                            if name not in self.files[product].keys():
                                self.files[product][name] = {}
                                self.files[product][name] = [filename]
                            else:
                                self.files[product][name].append(filename)
                                
            # Sort files by type
            files = []
            for track in self.files[product]:
                track_files = self.files[product][track]
                files = np.concatenate((files, track_files), axis=0)
                
            lbl_files = [file for file in files if "lbl" in file]
            img_files = [file for file in files if "img" in file]
            anc_files = [file for file in files if "anc" in file]
            srf_files = [file for file in files if "srf" in file]
            sim_files = [file for file in files if "sim" in file]

            logging.info(f' {product:<37} {str(len(lbl_files)):>7}' + 
                         f' {str(len(img_files)):>7} {str(len(anc_files)):>7}' + 
                         f' {str(len(srf_files)):>7} {str(len(sim_files)):>7}'
                        )
            

    def read_labels(self):
        """ Read and store in the Class some parameters from the label files
        """
        for product in self.files.keys():
            self.clock_lim[product] = {}
            self.epoch_lim[product] = {}
            self.lat_lim[product] = {}
            self.lon_lim[product] = {}
            for name in self.files[product].keys():
                lbl_filenames = [file for file in self.files[product][name] if '.lbl' in file]
                if lbl_filenames:
                    try:
                        lbl_filename = lbl_filenames[0]
                    except:
                        logging.error(f'{product}/{name} label file is corrupted or non-existent')
                    # Clock
                    lim1 = read.lbl_keyword(lbl_filename, 'START_TIME')
                    lim2 = read.lbl_keyword(lbl_filename, 'STOP_TIME')
                    self.clock_lim[product][name] = [lim1, lim2]
                    self.epoch_lim[product][name] = [datetime.strptime(lim1, "%Y-%m-%dT%H:%M:%S").timestamp(),
                                                     datetime.strptime(lim2, "%Y-%m-%dT%H:%M:%S").timestamp()]
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
        if img_filename and lbl_filename:
            anc, img = read.img(img_filename, lbl_filename)
            out = anc.to_dict(orient='list')
            out.update({'IMG':img})
            # Gain Correction    
            line = read.lbl_keyword(lbl_filename, 'Pmax', fullline=True)
            Pmax = float(line.split(' P')[1][:-1].split(' = ')[-1])
            Pmin = float(line.split(' P')[2][:-1].split(' = ')[-1])
            pdb = (255-img)*(Pmax-Pmin)/255+Pmin
            out.update({'Pmax':Pmax})
            out.update({'Pmin':Pmin})
            out.update({'IMG_pdb':pdb})
            
            
            return out#.update({'DATA':img})
        else:
            logging.warning('No orig data for ' + product + ' ' + name)

        
    def anc_data(self, product, name):
        """ Read anc data. It concatenates all columns from the files
            in the anc folder 
        
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
        if product == 'sln-l-lrs-5-sndr-ss-nfoc-power-v1.0':
            product = 'sln-l-lrs-5-sndr-ss-high-v2.0'
        files = self.files[product][name]
        anc_filenames = [file for file in files if os.path.join('anc','') in file]
        
        if anc_filenames:
            out = pd.DataFrame()
            for anc_filename in anc_filenames:
                df = pd.read_csv(anc_filename)
                out = pd.concat([out, df], axis=1)
            return out.to_dict(orient='list')
        else:
            logging.warning('No anc data for ' + product + ' ' + name)
   
        
    def srf_data(self, product, name, method='mouginot2010'):
        """ Read srf data. It concatenates all columns from the files
            in the anc folder 
        
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
        _files = self.files[product][name]
        files = [file for file in _files if method in file]
        anc_filenames = [file for file in files if os.path.join('srf','') in file]
        
        if anc_filenames:
            out = pd.DataFrame()
            for anc_filename in anc_filenames:
                df = pd.read_csv(anc_filename)
                out = pd.concat([out, df], axis=1)
            return out.to_dict(orient='list')
        else:
            logging.warning('No srf data for ' + product + ' ' + name)
   
        
    def sim_data(self, product, name, method='gerekos2018'):
        """ Read sim data.
        
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
        _files = self.files[product][name]
        files = [file for file in _files if method in file]
        sim_filenames = [file for file in files if os.path.join('sim','') in file]
        
        if sim_filenames:
            if product == 'sln-l-lrs-5-sndr-ss-nfoc-power-v1.0':
                orig_product = 'sln-l-lrs-5-sndr-ss-high-v2.0'
            else:
                orig_product = product
            out = self.orig_data(orig_product, name)
            # Replace with simulation files 
            out['IMG_pdb'] = np.loadtxt(sim_filenames[0], delimiter=",", dtype='float')
            return out
        else:
            logging.warning(f'No sim data for {product} {name} {method}')
    
    
    def matching_track(self, product1, name1, product2):
        """ Give the name of a track overlaping a track from another product
        
        ARGUMENT
        --------
        product1: string
            product considered
        name1: string
            name considered
        product2: string
            product to search a matching track within
        
        RETURN
        ------
            Name of the matching track from product2
        """
        time1s = self.epoch_lim[product1][name1]
        for name2 in self.epoch_lim[product2]:
            #logging.info(name2)
            time2s = self.epoch_lim[product2][name2]
            if (time2s[0] <= time1s[0] <= time2s[1]) or (time2s[0] <= time1s[1] <= time2s[1]):
                return name2
    
    
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

        products = copy.deepcopy(self.index_products())
        
        # Remove nfoc if present
        try:
            products.remove('sln-l-lrs-5-sndr-ss-nfoc-power-v1.0')
        except:
            pass
        
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
        
        
    def run(self, process, product, name, source='orig', archive=True, delete=False, method=None,
            non_standard_archive_path=None, **kwargs):
        """ Run a process
        
        ARGUMENT
        --------
        process: string
            name of the process, usually maps to functions in run.py
        product: string
            product full name or substring (e.g., sar05)
        name: string
            file identifier (e.g., '20071221033918')
        source: string ('orig' or 'sim')
            source of the input data
        archive: binary
            whether to archive
        delete: bit
            Force archive if file already exist
        non_standard_archive_path: string
            The archive path name if you do not wish to archive in the standard hierarchy
            
        RETURN
        ------
        results
        
        """
        # GET DATA
        # --------
        product = self.product_match(product)
        
        if source == 'orig':
            data = self.orig_data(product, name)
        elif source == 'sim':
            data = self.sim_data(product, name, method=method)
        
        # ARCHIVE NAME
        # ------------
        
        if process == 'anc':
            archive_path = os.path.join(self.xtra_path, process, product, name[:8] ,'data')
            filename = self.filename_root(product, name) + '_orig.txt'
            
        if process == 'srf':
            if not 'method':
                method = 'mouginot2010'
            archive_path = os.path.join(self.xtra_path, process, product, name[:8] ,'data')
            filename = self.filename_root(product, name) + f'_{method}.txt'
        
        if process == 'sgy':
            if source == 'sim':
                source = method
            archive_path = os.path.join(self.xtra_path, process, product, name[:8] ,'data')
            filename = self.filename_root(product, name) + f'_{source}.sgy'
            
        if non_standard_archive_path:
            archive_path = non_standard_archive_path
            
        archive_fullname = os.path.join(archive_path, filename)
        
        # RUN PROCESS
        #------------
        
        try:
            result = getattr(processing, process)(data, method=method, **kwargs)
        except:
            logging.warning(f'Exception for {process} {product} {name}')
            result = []
        else:
            # ARCHIVE
            #--------
            if archive:
                if not glob.glob(archive_fullname) or delete:
                    os.makedirs(archive_path, exist_ok=True)
                    if process == 'sgy':
                        result.write(archive_fullname, format='SEGY', data_encoding=5)  # encode 1 for IBM, 5 for IEEE
                    else:
                        result.to_csv(archive_fullname, header=True, index=False)
                    logging.info(' ' + archive_fullname + ' CREATED')
        
        return result
        
        
    def run_all(self, process, product, delete=False, archive=True,
                n_jobs=4, verbose=6, **kwargs):
        """ Run a process on all tracks/names within a product
        """
        logging.warning('Logging does not work with joblib.Parallel')
        product = self.product_match(product)
        names = self.files[product].keys()
        
        results = Parallel(n_jobs=n_jobs, verbose=verbose)(
            delayed(self.run)(process, product, name, **{'archive':archive ,
                                                       'delete':delete, 
                                                       #'method':method,
                                                       }, **kwargs) 
            for name in names)
        
        #for name in names:
        #    _ = self.run(process, product, name, 
        #             archive=archive, delete=delete, **kwargs)

            
    def plt_rdg(self, product, name, sim=False, ax=None, latlim=None,
                title=None, invertx=False, **kwargs):
        """ Plot a LRS radargram
        
        ARGUMENTS
        ---------
        product: string
            product full name or substring (e.g., sar05)
        name: string
            file identifier (e.g., '20071221033918')
        sim: binary
            Wether you want the simulation product for this track
        latlim: [float, float]
            latitude boundary
        ax: ax Object
            ax within which the radargram will be plotted
        ylim: [float, float]
            y limits of the plot
        title: string
            Title of the plot
        invertx: binary
            Whether to invert the x-axis
        **kwargs: tuple
            kwargs of matplotlib imshow
        
        RETURN
        ------
        rdg: array
            Radargram
        idx: Binary vector
            valid x bin
        
        """
        # Data
        # ----
        if sim:
            img = self.sim_data(product, name)
        else:
            img = self.orig_data(product, name)['IMG_pdb']
        anc = self.anc_data(product, name)
        #xlim = np.sort((np.where(anc['latitude'] <= latlim[0])[0][0], 
        #                np.where(anc['latitude'] <= latlim[1])[0][0]))
        latitude = np.array(anc['latitude'])
        if not latlim:
            latlim = [latitude[0], latitude[-1]]
        idx = self.wherelat(product, name, latlim)
    
        #idx = (latitude >= np.min(latlim)) & (
        #       latitude <= np.max(latlim))
        id1 = (np.where(idx)[0])[0]
        id2 = (np.where(idx)[0])[-1]
        #img = self.orig_data(product, name)['IMG'][:,xlim[0]:xlim[1]]
    
        # Plot
        # ----
    
        if not ax:
            fig, ax = plt.subplots(figsize=(16,5))
        
        ax.imshow(img, **kwargs)
        ax.set_xlim(id1, id2)
        if invertx:
            ax.invert_xaxis()
        
        #lat1 = anc['latitude'][xlim[0]]
        #lat2 = anc['latitude'][xlim[1]]
        
        
        #if not title:
        #    title = f'{product} - {name} ({latlim} latitude)' 
        #ax.set_title(title, fontsize=15)
    
        return img, idx

    
    def signalconversion(self, product, name, dn, calval=0):
        """ !!! DEPRECATED !!! 
        Convert the orig LRS signal to power. Note that the coefficients 
        of conversion varies for each processing and track. The coefficients 
        are extracted from the lbl files.
    
        ARGUMENTS
        ---------
        dn: vector of float
            signal from the orig data
        calval: float
            Calibration value in dB
        """
        
        # Find lbl file name
        files = self.files[product][name]
        try:
            lbl_filename = [file for file in files if '.lbl' in file][0]
        except IndexError:
            logging.warning('No orig data for ' + product + ' ' + name)
        
        # Get Conversion coefficients 
        line = read.lbl_keyword(lbl_filename, 'Pmax', fullline=True)
        Pmax = float(line.split(' P')[1][:-1].split(' = ')[-1])
        Pmin = float(line.split(' P')[2][:-1].split(' = ')[-1])
        
        # Conversion
        pdb = (255-dn)*(Pmax-Pmin)/255+Pmin
        out = pdb
        return out
        
        
    def wherelat(self, product, name, lim):
        """ return a binary vector indicating where latitudes 
        are within the indicated limits
    
        ARGUMENTS
        ---------
        lim: [float, float]
            latitude limits
        
        RETURN
        ------
        Binary vector
        """
        anc = self.anc_data(product, name)
        vec = np.array(anc['latitude'])
        out = (vec >= np.min(lim)) & (vec <= np.max(lim))
        
        return out
        
        
    def wherelon(self, product, name, lim):
        """ return a binary vector indicating where longitudes 
        are within the indicated limits
    
        ARGUMENTS
        ---------
        lim: [float, float]
            longitude limits
        
        RETURN
        ------
        Binary vector
        """
        anc = self.anc_data(product, name)
        vec = np.array(anc['longitude'])
        out = (vec >= np.min(lim)) & (vec <= np.max(lim))
        
        return out
        
        
    def wherelatlon(self, product, name, latlim, lonlim):
        """ return a binary vector indicating where longitudes 
        are within the indicated limits
    
        ARGUMENTS
        ---------
        latlim: [float, float]
            latitude limits
            
        lonlim: [float, float]
            longitude limits
        
        RETURN
        ------
        Binary vector
        """
        anc = self.anc_data(product, name)
        vec_lat = np.array(anc['latitude'])
        vec_lon = np.array(anc['longitude'])
        out = (vec_lat >= np.min(latlim)) & (vec_lat <= np.max(latlim)) & (vec_lon >= np.min(lonlim)) & (vec_lon <= np.max(lonlim))
        
        return out

    
    def lonlat2stereo(self, product, name, sampling=1000e3, use_anc=False):
        """ Convert longitude/latitude to xy stereographic
        """
        crs_lonlat = CRS.from_string("+proj=longlat +R=1737400 +no_defs")
        crs_stereo = CRS.from_proj4("+proj=stere +lat_0=-90 +lon_0=0 +k=1 +x_0=0 +y_0=0 +R=1737400 +units=m +no_defs +type=crs")
        transformer = Transformer.from_crs(crs_lonlat, crs_stereo)
        
        latlim = self.lat_lim[product][name]
        lonlim = self.lon_lim[product][name]
        if not use_anc:
            geo = tools.intermediate_latlon(latlim, lonlim, sampling=sampling)
            lon = geo['lons']
            lat = geo['lats']
        else:
            anc = self.anc_data(product, name)
            lon = anc['longitude']
            lat = anc['latitude']
        x, y = transformer.transform(lon, lat)
        return x, y
   

    def distance(self, product, name, sampling=1000e3):
        """ Give distance in meters between first and last points
        """
        moon_radius = 1737400
        geod = pyproj.Geod(ellps="sphere", a=moon_radius, b=moon_radius)
        
        latlim = self.lat_lim[product][name]
        lonlim = self.lon_lim[product][name]
        
        _, _, forward_distance = geod.inv(lonlim[0], latlim[0], lonlim[1], latlim[1])
        
        return forward_distance

        
class Track():
    """ Class for getting info on a groundtrack segment
    """
    def __init__(self, LRS, name, latlim=[-80,-70], lonlim=[0,360], 
                 get_missing=False, relative_shift=False):
        """ Get various parameters defining the dataset
        
        ARGUMENTS
        ---------
        LRS: Class
            LRS class
        name: string
            Name of a SWH file
        latlim: [float, float]
            latitude min/max boundaries
        latlim: [float, float]
            longitude min/max boundaries
        get_missing: binary
            download missing data (BETA!)
        relative_shift: binary
            Whether to try correcting the range delay on sar data to align with swh radargrams
        """
        self.LRS = LRS
        self.latlim = latlim
        self.lonlim = lonlim
        # Products
        self.swh = {'product':'sln-l-lrs-5-sndr-ss-high-v2.0'}
        self.swh_sim = {'product':'sln-l-lrs-5-sndr-ss-high-v2.0'}
        self.sar05 = {'product':'sln-l-lrs-5-sndr-ss-sar05-power-v1.0'}
        self.sar10 = {'product':'sln-l-lrs-5-sndr-ss-sar10-power-v1.0'}
        #self.sar40 = {'product':'sln-l-lrs-5-sndr-ss-sar40-power-v1.0'}
        self.nfoc_sim = {'product':'sln-l-lrs-5-sndr-ss-nfoc-power-v1.0'}
        # Names
        self.swh['name'] = name
        self.swh_sim['name'] = self.swh['name']
        self.sar05['name'] = LRS.matching_track(self.swh['product'], 
                                                self.swh['name'], 
                                                self.sar05['product'])
        self.sar10['name'] = LRS.matching_track(self.swh['product'], 
                                                self.swh['name'], 
                                                self.sar10['product'])
        #self.sar40['name'] = LRS.matching_track(self.swh['product'], 
        #                                        self.swh['name'], 
        #                                        self.sar40['product'])
        self.nfoc_sim['name'] = self.swh['name']
        # Download
        if get_missing == True:
            self.get_missing()
        # Indices
        self.idx = LRS.wherelatlon(self.swh['product'], self.swh['name'], self.latlim, self.lonlim)
        self.length = len(self.idx[self.idx == True])
        # Ancilliary data
        self.anc = LRS.anc_data(self.swh['product'], self.swh['name'])
        self.latitude = np.array(self.anc['latitude'])[self.idx]
        self.longitude = np.array(self.anc['longitude'])[self.idx]
        self.altitude = np.array(self.anc['altitude'])[self.idx]
        self.range0 = np.array(self.anc['range0'])[self.idx]
        self.date = np.array(self.anc['date'])[self.idx]
        self.time = np.array(self.anc['time'])[self.idx]
        # Non-swh indices
        self.index()
        # Surface
        self.surface()
        # Range Shift
        self.relative_shift = relative_shift
        self.range_shift()
        # Radargrams
        self.rdg()
    
    
    def get_missing(self):
        
        # Download orig files
        #for ext in ['lbl', 'img']:
        #    _ = self.LRS.download(self.swh['product'], self.swh['name'], typ=ext)
        #    _ = self.LRS.download(self.sar05['product'], self.sar05['name'], typ=ext)
        #    _ = self.LRS.download(self.sar10['product'], self.sar10['name'], typ=ext)
        #    _ = self.LRS.download(self.sar40['product'], self.sar40['name'], typ=ext)
        #self.LRS = Env()
        
        # anc processing
        _ = self.LRS.run('anc', self.swh['product'], self.swh['name'], archive=True)
        _ = self.LRS.run('anc', self.sar05['product'], self.sar05['name'], archive=True)
        _ = self.LRS.run('anc', self.sar10['product'], self.sar10['name'], archive=True)
        #_ = self.LRS.run('anc', self.sar40['product'], self.sar40['name'], archive=True)
        #self.LRS = Env()
        
        # srf processing
        #for method in ['mouginot2010', 'grima2012']:
        #    _ = self.LRS.run('srf', self.swh['product'], self.swh['name'], method=method)
        #    _ = self.LRS.run('srf', self.sar05['product'], self.sar05['name'], method=method)
        #    _ = self.LRS.run('srf', self.sar10['product'], self.sar10['name'], method=method)
        #    _ = self.LRS.run('srf', self.sar40['product'], self.sar40['name'], method=method)
        #self.LRS = Env()
        
    
    def index(self):
        """Indices within latlim and lonlim for each products
        """
        #idx_binary = self.LRS.wherelat(self.swh['product'], self.swh['name'], self.latlim)
        idx_binary = self.LRS.wherelatlon(self.swh['product'], self.swh['name'], self.latlim, self.lonlim)
        self.swh['index'] = np.arange( len(idx_binary) )[idx_binary]
        self.swh_sim['index'] = self.swh['index']
        
        idx0 = np.where(self.LRS.anc_data(self.sar05['product'], self.sar05['name'])['time'] > self.time[0])[0][0]
        self.sar05['index'] = np.arange(idx0, idx0+self.length, 1)
        
        idx0 = np.where(self.LRS.anc_data(self.sar10['product'], self.sar10['name'])['time'] > self.time[0])[0][0]
        self.sar10['index'] = np.arange(idx0, idx0+self.length, 1)
        
        #idx0 = np.where(self.LRS.anc_data(self.sar40['product'], self.sar40['name'])['time'] > self.time[0])[0][0]
        #self.sar40['index'] = np.arange(idx0, idx0+self.length, 1)
        
        self.nfoc_sim['index'] = self.swh['index']
    
    
    def surface(self):
        """ Surface echo
        """
        self.swh['srf'] = {}
        self.sar05['srf'] = {}
        self.sar10['srf'] = {}
        #self.sar40['srf'] = {}
        for method in ['mouginot2010', 'grima2012']:
            self.swh['srf'][method] = {}
            self.sar05['srf'][method] = {}
            self.sar10['srf'][method] = {}
            #self.sar40['srf'][method] = {}
            for n in ['y', 'pdb']:
                l = len(self.swh['index'])
                
                arr = self.LRS.srf_data(self.swh['product'], self.swh['name'], 
                                        method=method)[n][self.swh['index'][0]:self.swh['index'][0]+l]
                self.swh['srf'][method][n] = np.array(arr)
                
                arr = self.LRS.srf_data(self.sar05['product'], self.sar05['name'], 
                                        method=method)[n][self.sar05['index'][0]:self.sar05['index'][0]+l]
                self.sar05['srf'][method][n] = np.array(arr)
                
                arr = self.LRS.srf_data(self.sar10['product'], self.sar10['name'], 
                                        method=method)[n][self.sar10['index'][0]:self.sar10['index'][0]+l]
                self.sar10['srf'][method][n] = np.array(arr)
                
                #arr = self.LRS.srf_data(self.sar40['product'], self.sar40['name'], 
                #                        method=method)[n][self.sar40['index'][0]:self.sar40['index'][0]+l]
                #self.sar40['srf'][method][n] = np.array(arr)
                
            # Upsampling to match 24m/pixel in range (i.e., same as far)
            self.swh['srf'][method]['y'] = self.swh['srf'][method]['y']*2
    
    
    def range_shift(self, s=3e6):
        """ Range shit for SAR data
        """
        
        # Get surface picks
        y = self.swh['srf']['mouginot2010']['y']
        x = np.arange(len(y))
        
        f = UnivariateSpline(x, y, s=s)
        y_smooth = f(x)
        
        y_constant_shift = np.full(len(y), 400-np.mean(y), dtype=int)
        y_constant_shift_sim = np.full(len(y), -900, dtype=int)
        y_relative_shift = np.array(y_smooth, dtype=int)-200
        
        self.swh['range_shift'] = y_constant_shift
        self.swh_sim['range_shift'] = y_constant_shift_sim
        self.nfoc_sim['range_shift'] = y_constant_shift_sim
        if self.relative_shift:
            self.sar05['range_shift'] = y_constant_shift + y_relative_shift
        else:
            self.sar05['range_shift'] = y_constant_shift
        self.sar10['range_shift'] = self.sar05['range_shift']
        #self.sar40['range_shift'] = self.sar05['range_shift']
    
    
    def distance(self, vec=False):
        """ Distance between start and end points
        """
        moon_radius = 1737400
        geod = pyproj.Geod(a=moon_radius, b=moon_radius)
        
        _, _, forward_distance = geod.inv(self.longitude[0], self.latitude[0], 
                                          self.longitude[-1], self.latitude[-1])
        out = forward_distance
        if vec:
            out = np.linspace(0, forward_distance, self.length)
        
        return out
    
    
    def rdg(self):
        """ Radargrams
        """
        l = len(self.swh['index'])
        rdg = self.LRS.orig_data(self.swh['product'], self.swh['name'])['IMG_pdb']
        # Upsampling to match 24m/pixel in range (i.e., same as far)
        rdg = rdg.repeat(2, axis=0)
        self.swh['rdg'] = rdg[:,self.swh['index'][0]:self.swh['index'][0]+l]
        
        rdg = self.LRS.orig_data(self.sar05['product'], self.sar05['name'])['IMG_pdb']
        self.sar05['rdg'] = rdg[:,self.sar05['index'][0]:self.sar05['index'][0]+l]
        
        rdg = self.LRS.orig_data(self.sar10['product'], self.sar10['name'])['IMG_pdb']
        self.sar10['rdg'] = rdg[:,self.sar10['index'][0]:self.sar10['index'][0]+l]
        
        #rdg = self.LRS.orig_data(self.sar40['product'], self.sar40['name'])['IMG_pdb']
        #self.sar40['rdg'] = rdg[:,self.sar40['index'][0]:self.sar40['index'][0]+l]
        
        try: # No swh simulation avaialble
            rdg = self.LRS.sim_data(self.swh_sim['product'], self.swh_sim['name'])
            self.swh_sim['rdg'] = rdg[:,self.swh_sim['index'][0]:self.swh_sim['index'][0]+l]
        except:
            self.swh_sim['rdg'] = self.swh['rdg']*0-255
        
        try: # No nfoc simulation avaialble
            rdg = self.LRS.sim_data(self.nfoc_sim['product'], self.nfoc_sim['name'])
            self.nfoc_sim['rdg'] = rdg[:,self.nfoc_sim['index'][0]:self.nfoc_sim['index'][0]+l]
        except:
            self.nfoc_sim['rdg'] = self.swh['rdg']*0-255
        
        # Shift radargrams
        for i in np.arange(l):
            try:
                self.swh['rdg'][:, i] = np.roll(self.swh['rdg'][:, i], self.swh['range_shift'][i])
                self.swh_sim['rdg'][:, i] = np.roll(self.swh_sim['rdg'][:, i], self.swh_sim['range_shift'][i])
                self.nfoc_sim['rdg'][:, i] = np.roll(self.nfoc_sim['rdg'][:, i], self.nfoc_sim['range_shift'][i])
                self.sar05['rdg'][:, i] = np.roll(self.sar05['rdg'][:, i], self.sar05['range_shift'][i])
                self.sar10['rdg'][:, i] = np.roll(self.sar10['rdg'][:, i], self.sar10['range_shift'][i])
                #self.sar40['rdg'][:, i] = np.roll(self.sar40['rdg'][:, i], self.sar40['range_shift'][i])
            except:
                pass
    
    
    def stereo(self, crs_lonlat = '+proj=longlat +R=1737400 +no_defs',
              crs_stereo = '+proj=stere +lat_0=-90 +lon_0=0 +k=1 +x_0=0 +y_0=0 +R=1737400 +units=m +no_defs +type=crs'):
        """ Convert longitude/latitude to xy stereographic
        """
        transformer = Transformer.from_crs(CRS.from_string(crs_lonlat), 
                                           CRS.from_proj4(crs_stereo))
        x, y = transformer.transform(self.longitude, self.latitude)
        return np.array(x), np.array(y)#{'x':x, 'y':y}
    
    
    def browse(self, cmap='gray_r'):
        """
        """
        products = [self.swh['product'],
                    self.sar05['product'],
                    self.sar10['product'],
                    self.sar40['product'],
                   ]
        names = [self.swh['name'],
                 self.sar05['name'],
                 self.sar10['name'],
                 self.sar40['name'],
                ]
    
        fig, axes = plt.subplot_mosaic(
            [[products[0]],
             [products[1]],
             [products[2]], 
             #[products[3]], 
            ], constrained_layout=True, figsize=(19,9)
            )#figsize=(19,9), constrained_layout=True, dpi=500)
        fig.set_size_inches(16, 8)
        fig.set_dpi(500)
        
        # ----------
        # Radargrams
        # ----------
    
        axes[products[0]].imshow(self.swh['rdg'], cmap=cmap, vmin=-130, vmax=-80)
        axes[products[1]].imshow(self.sar05['rdg'], cmap=cmap, vmin=-10, vmax=40)
        axes[products[2]].imshow(self.sar10['rdg'], cmap=cmap, vmin=-10, vmax=40)
        #axes[products[3]].imshow(self.sar40['rdg'], cmap=cmap, vmin=-10, vmax=40)
             
        for i in [0,1,2]:
            axes[products[i]].set_title(f'{products[i]} - {names[i]}', y=.86)
            axes[products[i]].set_yticks(np.arange(0,3000, 1000/24))
            axes[products[i]].set_yticklabels([])
            if i != 0:
                axes[products[i]].sharey(axes[products[0]])
            #axes[products[i]].set_xlabel('bin #')
    
        axes[products[0]].set_ylim([1000,0])
        #axes[products[1]].set_ylim([1000,0])
        #axes[products[2]].set_ylim([1900,900])
        
        
if __name__ == "__main__":
    # execute only if run as a script
    main()

        
def main():
    """ Test Env
    """
    pass
