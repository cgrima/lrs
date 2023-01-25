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
import urllib.request
from shapely.geometry import Point, Polygon
from joblib import Parallel, delayed
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
        self.data_path = root_path + 'data/'
        self.code_path = root_path + 'code/'
        self.orig_path = self.data_path + 'orig/lrs/'
        self.xtra_path = self.data_path + 'xtra/lrs/'
        self.files = {}
        self.clock_lim = {}
        self.lat_lim = {}
        self.lon_lim = {}
        self.products = self.index_products()
        self.index_files()
        self.read_labels()
        
        
    def index_products(self, path=False):
        """List available products
        """
        out = os.listdir(self.orig_path)
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

        
    def download(self, product, name, typ='img', delete=False):
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
        Nothing
        
        """
        filename = 'LRS_' + product.split('-')[6].upper() + 'KM_' + name + '.' + typ
        relative_path = os.path.join(product, name[:8], 'data')
        #remote_file = os.path.join(self.remote_host, relative_path, filename)
        remote_file = urllib.parse.urljoin(self.remote_host, relative_path + '/' + filename)
        print(remote_file)
        local_file = os.path.join(self.orig_path, relative_path, filename)
        
        if not glob.glob(local_file) or delete:
            os.makedirs(os.path.join(self.orig_path, relative_path), exist_ok=True)
            _ = urllib.request.urlretrieve(remote_file, local_file)
            logging.info(' ' + local_file + ' DOWNLOADED')
        
        
    def index_files(self):
        """ Index all data files 
        """
        for product in self.products:
            # Indicate below what folders need to be indexed
            index_paths = [os.path.join(self.orig_path, product),
                           os.path.join(self.xtra_path, 'aux', product),
                           os.path.join(self.xtra_path, 'srf', product),]
            
            self.files[product] = {}
            for path in index_paths:
                if os.path.exists(path):
                    for day in os.listdir(path):
                        filenames = glob.glob(path + '/' + day + '/data/*.*')
                        for filename in filenames:
                            name = filename.split('KM_')[-1][:14]
                            if name not in self.files[product].keys():
                                self.files[product][name] = {}
                                self.files[product][name] = [filename]
                            else:
                                self.files[product][name].append(filename)

            logging.info(' ' + product + ' has ' + 
                         str(len(self.files[product])) + ' tracks')

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
        try:
            lbl_filename = [file for file in files if '.lbl' in file][0]
            img_filename = [file for file in files if '.img' in file][0]
        except IndexError:
            logging.warning('No orig data for ' + product + ' ' + name)
        else:
            aux, img = read.img(img_filename, lbl_filename)
            out = aux.to_dict(orient='list')
            out.update({'IMG':img})
            out.update({'IMG_pdb':self.signalconversion(product, name, img)})
            return out#.update({'DATA':img})

        
    def aux_data(self, product, name):
        """ Read aux data. It concatenates all columns from the files
            in the aux folder 
        
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
        aux_filenames = [file for file in files if '/aux/' in file]
        
        if aux_filenames:
            out = pd.DataFrame()
            for aux_filename in aux_filenames:
                df = pd.read_csv(aux_filename)
                out = pd.concat([out, df], axis=1)
            return out.to_dict(orient='list')
        else:
            logging.warning('No aux data for ' + product + ' ' + name)
   
        
    def srf_data(self, product, name):
        """ Read srf data. It concatenates all columns from the files
            in the aux folder 
        
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
        aux_filenames = [file for file in files if '/srf/' in file]
        
        if aux_filenames:
            out = pd.DataFrame()
            for aux_filename in aux_filenames:
                df = pd.read_csv(aux_filename)
                out = pd.concat([out, df], axis=1)
            return out.to_dict(orient='list')
        else:
            logging.warning('No srf data for ' + product + ' ' + name)
            
        
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

        products = self.index_products()
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
        
        
    def run(self, process, product, name, archive=False, delete=False, **kwargs):
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
        
        if process == 'aux':
            data = self.orig_data(product, name)
            archive_path = self.xtra_path + '/'.join([process, product, 
                                                     name[:8] ,'data'])
            suffix = '_orig.txt'
            filename = 'LRS_' + product.split('-')[-3].upper() + 'KM_' + name + suffix
            
            archive_fullname = '/'.join([archive_path, filename])
            
        if process == 'srf':
            if not hasattr(kwargs, 'method'):
                logging.warning('You need to define a method for processing.srf(). Default: mouginot2010')
                method = 'mouginot2010'
            data = self.orig_data(product, name)
            archive_path = self.xtra_path + '/'.join([process, product, 
                                                     name[:8] ,'data'])
            suffix = f'_{method}.txt'#'_orig.txt'
            filename = 'LRS_' + product.split('-')[-3].upper() + 'KM_' + name + suffix
            
            archive_fullname = '/'.join([archive_path, filename])
        
        # RUN PROCESS
        #------------
        
        try:
            result = getattr(processing, process)(data, **kwargs)
        except:
            result = []
        else:
            
        # ARCHIVE
        #--------
        
            if archive:
                if not glob.glob(archive_fullname) or delete:
                    os.makedirs(archive_path, exist_ok=True)
                    result.to_csv(archive_fullname, header=True, index=False)
                    logging.info(' ' + archive_fullname + ' CREATED')
        
            return result
        
        
    def run_all(self, process, product, delete=False, 
                n_jobs=4, verbose=6, **kwargs):
        """ Run a process on all tracks/names within a product
        """
        product = self.product_match(product)
        names = self.files[product].keys()
        
        results = Parallel(n_jobs=n_jobs, verbose=verbose)(
            delayed(self.run)(process, product, name, {'delete':delete, **kwargs}) 
            for name in names)
        
        for name in names:
            _ = self.run(process, product, name, 
                     archive=True, delete=delete, **kwargs)

            
    def plt_rdg(self, product, name, ax=None, latlim=None,
                title=None, **kwargs):
        """ Plot a LRS radargram
        
        ARGUMENTS
        ---------
        product: string
            product full name or substring (e.g., sar05)
        name: string
            file identifier (e.g., '20071221033918')
        latlim: [float, float]
            latitude boundary
        ax: ax Object
            ax within which the radargram will be plotted
        ylim: [float, float]
            y limits of the plot
        title: string
            Title of the plot
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
    
        img = self.orig_data(product, name)['IMG_pdb']
        aux = self.aux_data(product, name)
        #xlim = np.sort((np.where(aux['latitude'] <= latlim[0])[0][0], 
        #                np.where(aux['latitude'] <= latlim[1])[0][0]))
        latitude = np.array(aux['latitude'])
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
        
        #lat1 = aux['latitude'][xlim[0]]
        #lat2 = aux['latitude'][xlim[1]]
        
        
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
        aux = self.aux_data(product, name)
        vec = np.array(aux['latitude'])
        out = (vec >= np.min(lim)) & (vec <= np.max(lim))
        
        return out
    

if __name__ == "__main__":
    # execute only if run as a script
    main()

        
def main():
    """ Test Env
    """
    pass
