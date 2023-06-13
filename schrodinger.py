# ---------------------------------------
# Some tools for the Schrodinger project
# --------------------------------------

import numpy as np
import os
import lrs
import matplotlib.pyplot as plt
import scipy
import copy
import pandas as pd
import glob
import logging
from . import Classdef, read, tools, processing



def simulation_integration(LRS, mat_filename, archive=False, delete=False):
    """ Integrates Chris' cluttergrams (.mat) into the hierarchy
    """
    # Get Data
    mat = scipy.io.loadmat(mat_filename)
    name = mat_filename.split('Cluttersim_')[1].split('_')[0]
    rdg = LRS.orig_data('sln-l-lrs-5-sndr-ss-high-v2.0', name)['IMG_pdb']
    anc = LRS.anc_data('sln-l-lrs-5-sndr-ss-high-v2.0', name)
    
    # Padding
    padding_value = -202.9 # Same as in LRS orig data
    ctg_blank = np.full((np.shape(mat['RgramRCPWR'])[0], np.shape(rdg)[1]), padding_value)
    
    ctg_RCPWR = copy.deepcopy(ctg_blank)
    ctg_FCPWR = copy.deepcopy(ctg_blank)
    
    ctg_RCPWR[:,mat['Xindex'][0]] = mat['RgramRCPWR']
    ctg_FCPWR[:,mat['Xindex'][0]] = mat['RgramFocPWR']
    
    # Archive
    archive_path_RCPWR = os.path.join(LRS.xtra_path, 'sim', 'sln-l-lrs-5-sndr-ss-high-v2.0', name[:8] ,'data')
    archive_path_FCPWR = os.path.join(LRS.xtra_path, 'sim', 'sln-l-lrs-5-sndr-ss-nfoc-power-v1.0', name[:8] ,'data')
    
    archive_fullname_RCPWR = os.path.join(archive_path_RCPWR, f'LRS_SIM_{name}_gerekos2018.csv')
    archive_fullname_FCPWR = os.path.join(archive_path_FCPWR, f'LRS_SIM_{name}_gerekos2018.csv')
    
    if archive:
        # RCPWR
        archive_path = archive_path_RCPWR
        archive_fullname = archive_fullname_RCPWR
        result = pd.DataFrame(ctg_RCPWR)
        if not glob.glob(archive_fullname) or delete:
            os.makedirs(archive_path, exist_ok=True)
            result.to_csv(archive_fullname, header=True, index=False)
            logging.info(' ' + archive_fullname + ' CREATED')
        # FCPWR
        archive_path = archive_path_FCPWR
        archive_fullname = archive_fullname_FCPWR
        result = pd.DataFrame(ctg_FCPWR)
        if not glob.glob(archive_fullname) or delete:
            os.makedirs(archive_path, exist_ok=True)
            result.to_csv(archive_fullname, header=True, index=False)
            logging.info(' ' + archive_fullname + ' CREATED')



def browse_figure(LRS, swh_name, latlim=[-80,-70], lonlim=[105, 160], cmap='gray_r', vmin=-10, vmax=40, archive=False, relative_shift=False,
                 background_map='../schrodinger/figures/browse_map_swh.jpg'):
    """ Generate a browse figure for a track across Schrodinger
    
    Example
    -------
    
    import schrodinger
    import lrs
    LRS = lrs.Classdef.Env()
    schrodinger.browse_figure(LRS, '20080409215959')
    """
    # --------
    # Get data
    # --------
    t = :wqClassdef.Track(LRS, swh_name, latlim=latlim, lonlim=lonlim, relative_shift=relative_shift)
    
    products = [t.swh['product'],
                t.sar05['product'],
                t.nfoc_sim['product'], ]
    
    names = [t.swh['name'],
             t.sar05['name'],
             t.nfoc_sim['name'], ]
    
    rdgs = [t.swh['rdg'],
            t.sar05['rdg'],
            t.nfoc_sim['rdg'], ]
    
    # Figure
    fig, axes = plt.subplot_mosaic(
        [["map", "map", "map", "map", "map", products[0], products[0], products[0], products[0], products[0], products[0]],
         ["map", "map", "map", "map", "map", products[1], products[1], products[1], products[1], products[1], products[1]],
         ["map", "map", "map", "map", "map", products[2], products[2], products[2], products[2], products[2], products[2]]], 
    )#figsize=(19,9), constrained_layout=True, dpi=500)
    
    axes['map'].get_yaxis().set_visible(False)
    
    # -----------
    # Coordinates
    # -----------
    
    x, y = t.stereo()
    if (x[-1]-x[0]) < 1:
        invertx = True
    else:
        invertx = False
        
    # ----------
    # Radargrams
    # ----------
    
    cmap_range = 50
    axes[products[0]].imshow(rdgs[0], cmap=cmap, vmin=-130, vmax=-130+cmap_range, )
    axes[products[1]].imshow(rdgs[1], cmap=cmap, vmin=-10, vmax=-10+cmap_range, )
    axes[products[2]].imshow(rdgs[2], cmap=cmap, vmin=-40, vmax=-40+cmap_range, )
    
    for i in [0,1,2]:
        axes[products[i]].set_title(f'{products[i]} - {names[i]}', y=.86)
        axes[products[i]].set_yticks(np.arange(0,3000, 1000/24))
        axes[products[i]].set_yticklabels([])
        axes[products[i]].set_ylim([1000,0])
        if invertx:
            axes[products[i]].invert_xaxis()
        if i == 2:
            axes[products[i]].set_title('[SIM] ' + f'{products[i]} - {names[i]}', y=.86)
            axes[products[i]].set_xlabel('Relative bin #')
    
    # ---
    # Map
    # ---
    
    axes['map'].set_xlim(100000, 550000)
    axes['map'].set_ylim(-550000, -100000)
    
    axes['map'].plot(x, y)
    
    if invertx:
        axes['map'].plot(x[-1], y[-1], marker="o", markersize=10, color='white')
    else:
        axes['map'].plot(x[0], y[0], marker="o", markersize=10, color='white')
    
    img = plt.imread(background_map)
    axes['map'].imshow(img, aspect='equal', extent=(100000, 550000, -550000, -100000))

    axes['map'].plot(x, y, color='white')
    axes['map'].get_xaxis().set_visible(False)
    
    # -------------
    # 50-km markers
    # -------------
    
    # Marker rotation
    mark_angle = np.rad2deg(np.arctan((y[-1]-y[0])/(x[-1]-x[0])))
    
    # Marker spacing
    #km = np.sqrt(np.array(x)**2+np.array(y)**2)/1000
    km = t.distance(vec=True)/1000.
    km_sampling = len(km)/km.max()
    km_marks = np.arange(0, km.max(), 50)
    
    for km_mark in km_marks:
        # Markers on radargrams
        axes[products[0]].axvline(x = km_mark*km_sampling, color = 'k', ls = '--', alpha=.5, lw=.5)
        axes[products[1]].axvline(x = km_mark*km_sampling, color = 'k', ls = '--', alpha=.5, lw=.5)
        axes[products[2]].axvline(x = km_mark*km_sampling, color = 'k', ls = '--', alpha=.5, lw=.5)
        # Markers on map
        idx_mark = int(km_mark*km_sampling)
        axes['map'].plot(x[idx_mark], y[idx_mark], marker=(2,0,mark_angle), markersize=10, markeredgecolor="w", markerfacecolor="w")
    
    
    # -------
    # Archive
    # -------
    
    fig.set_size_inches(16, 8)
    fig.set_dpi(500)
    
    if archive == True:
        plt.subplots_adjust(wspace=0.1,hspace=0.1,left=.01,right=.98,bottom=.03,top=.97)
        maxlon = np.max(t.longitude)
        if relative_shift:
            suffix = '_rs'
        else:
            suffix = ''
        filename = f'LRS_schrodinger_{str(int(maxlon*1000)).zfill(6)[:6]}{suffix}.jpg'
        archive_path = os.path.join('..', 'schrodinger', 'browse', filename)
        #print(archive_path)
        plt.savefig(archive_path, dpi=500)
        print(archive_path)
        plt.clf()
        plt.close()