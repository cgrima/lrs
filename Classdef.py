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
from datetime import datetime
from shapely.geometry import Point, Polygon
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

        
    def download(self, product, name, typ='lbl', delete=False):
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
        
        RETURN
        ------
        Path to the local filename downloaded
        
        """
        #filename = 'LRS_' + product.split('-')[6].upper() + 'KM_' + name + '.' + typ6 
        filename = self.filename_root(product, name) + '.' + typ
        #relative_path = os.path.join(product, name[:8], 'data')
        #remote_file = os.path.join(self.remote_host, relative_path, filename)
        remote_file = urllib.parse.urljoin(self.remote_host, product + '/' + name[:8] + '/data' + '/' + filename)
        local_file = os.path.join(self.orig_path, product, name[:8], 'data', filename)
        
        if not glob.glob(local_file) or delete:
            os.makedirs(os.path.join(self.orig_path, product, name[:8], 'data'), exist_ok=True)
            response = requests.get(remote_file)
            open(local_file, "wb").write(response.content)
            #_ = urllib.request.urlretrieve(remote_file, local_file)
            logging.info(' ' + local_file + ' DOWNLOADED')
        else:
            logging.info(' ' + local_file + ' EXISTS (NOT DOWNLOADED)')
            
        return local_file
    
    
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
                    lbl_filename = lbl_filenames[0]
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
            out.update({'IMG_pdb':self.signalconversion(product, name, img)})
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
            out = np.loadtxt(sim_filenames[0], delimiter=",", dtype='float')
            return out
        else:
            logging.warning('No sim data for ' + product + ' ' + name)
    
    
    def matching_track(self, product1, name1, product2):
        """ Give the name of a trach overlaping a track from another product
        
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
        products.remove('sln-l-lrs-5-sndr-ss-nfoc-power-v1.0')
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
        
        
    def run(self, process, product, name, archive=True, delete=False, 
            **kwargs):
        """ Run a process
        
        ARGUMENT
        --------
        process: string
            name of the process, usually maps to functions in run.py
        product: string
            product full name or substring (e.g., sar05)
        name: string
            file identifier (e.g., '20071221033918')
        archive: binary
            whether to archive
        delete: bit
            Force archive if file already exist
            
        RETURN
        ------
        results
        
        """
        product = self.product_match(product)
        
        # ARCHIVE NAME
        # ------------
        
        if process == 'anc':
            method = None
            data = self.orig_data(product, name)
            archive_path = os.path.join(self.xtra_path, process, product, 
                                                     name[:8] ,'data')
            suffix = '_orig.txt'
            filename = self.filename_root(product, name) + suffix
            
            archive_fullname = os.path.join(archive_path, filename)
            
        if process == 'srf':
            if 'method' in kwargs:
                method = kwargs['method']
            else:
                logging.warning('You need to define a method for processing.srf(). Default is mouginot2010')
                method = 'mouginot2010'
            data = self.orig_data(product, name)
            archive_path = os.path.join(self.xtra_path, process, product, 
                                                     name[:8] ,'data')
            suffix = f'_{method}.txt'
            filename = self.filename_root(product, name) + suffix
            
            archive_fullname = os.path.join(archive_path, filename)
        
        if process == 'sgy':
            method = None
            data = self.orig_data(product, name)
            archive_path = os.path.join(self.xtra_path, process, product, 
                                                     name[:8] ,'data')
            suffix = '_orig.sgy'
            filename = self.filename_root(product, name) + suffix
            
            archive_fullname = os.path.join(archive_path, filename)
            
        
        # RUN PROCESS
        #------------
        
        try:
            result = getattr(processing, process)(data, method=method)
        except:
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
        """ Convert the orig LRS signal to power. Note that the coefficients 
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
        return x, y#{'x':x, 'y':y}
        
        
if __name__ == "__main__":
    # execute only if run as a script
    main()

        
def main():
    """ Test Env
    """
    pass
