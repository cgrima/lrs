# LRS
Tools for manipulating Lunar Radar Sounder (LRS) data from the JAXA's Kaguya 
spacecraft. Data available at [JAXA's Data ARchives and Transmission System (DARTS) ](https://darts.isas.jaxa.jp/planet/pdap/selene/index.html.en).

## Working Directory

The hierarchy of the working directory is assumed to be 

```bash
./code/
    lrs/ # This repository
./data/
    orig/ # Original products
        lrs/ # LRS products provided by JAXA
            sln-l-lrs-5-sndr-ss-sar05-power-v1.0/
            sln-l-lrs-5-sndr-ss-sar10-power-v1.0/
            [...]
    xtra/ # Derived products that follow the orig hierarchy
        lrs/
            aux/ # Auxilliary data derived from orig 
                sln-l-lrs-5-sndr-ss-sar05-power-v1.0/
                sln-l-lrs-5-sndr-ss-sar10-power-v1.0/
            srf/ # Surface data derived from orig 
                sln-l-lrs-5-sndr-ss-sar05-power-v1.0/
                sln-l-lrs-5-sndr-ss-sar10-power-v1.0/
            [...]
    gis/ # Some GIS-ready data
        lrs/
./[...]
```

## Data Download

To download data from a given processing mode (e.g. `sln-l-lrs-5-sndr-ss-sar05-
power-v1.0`), but without `*.img` and `*.jpg` files to download the data
hierarchy without the largest files (`man lftp` for additional options):

```bash
cd data/orig
lftp -c "open https://data.darts.isas.jaxa.jp/pub/pds3; mirror -c -P 10 --only-missing -X '*.img' -X '*.jpg' sln-l-lrs-5-sndr-ss-sar05-power-v1.0/"
```

To download data related to a specific orbit:
(e.g. `LRS_SAR05KM_20071221093226`)

```bash
cd data/orig
lftp -c "open https://data.darts.isas.jaxa.jp/pub/pds3; mirror -c -P 10 --only-missing -I 'LRS_SAR05KM_20071221093226*' sln-l-lrs-5-sndr-ss-sar05-power-v1.0/"
```

## Initialisation

Create an instance that will hold basic information about the LRS dataset.
By default, any python command is assumed to be launched from within
the `./code` directory. If note, please change the keyword `root_path`.

```bash
# Initiate instance
LRS = lrs.Classdef.Env(root_path='../')
```


## Basic Data Info from Label Files

Basic requests from data within the label files:

```bash
# Get available file names
LRS.files['sln-l-lrs-5-sndr-ss-sar40-power-v1.0']['20071219231328']
>> ['../data/orig/sln-l-lrs-5-sndr-ss-sar40-power-v1.0/20071219/data/LRS_SAR40KM_20071219231328.lbl']

# Get start and stop latitude
LRS.lat_lim['sln-l-lrs-5-sndr-ss-sar40-power-v1.0']['20071219231328']
>> [-35.961, 75.148]

# Get start and stop spacecraft clock time
LRS.clock_lim['sln-l-lrs-5-sndr-ss-sar40-power-v1.0']['20071219231328']
>> [882141206, 882143419]
```

## Load Original Data

To load original data from a track in a friendly format:

```bash
# Load original data
data = LRS.orig_data['sln-l-lrs-5-sndr-ss-sar05-power-v1.0']['20071221033918']

# The function above also accepts any matching substrings for the product, e.g.
data = LRS.orig_data['sar05']['20071221033918']

# Display keys contained in the data
data.keys()
>> dict_keys(['OBSERVATION_TIME', 'DELAY', 'START_STEP', 'SUB_SPACECRAFT_LATITUDE', 'SUB_SPACECRAFT_LONGITUDE', 'SPACECRAFT_ALTITUDE', 'DISTANCE_TO_RANGE0', 'TI', 'IMG'])
```

## Run processings

The `./data/lrs/xtra/` folder will store derived data product with the same hierarchy as in the `orig` directory. 

### Auxiliary Data

To extract and archive auxiliary data from the header of the LRS orig files
```bash
_ = LRS.run('aux', 'sar05', '20071221033918', archive=True, delete=True)
```

### Surface Echo

TODO

### Batch processing

To run a processing on all the available data using 8 cores in parallel:

```bash
LRS.run_all('aux', 'sar05', delete=False, n_jobs=8)
```

## Geographic Query

### From Orig Labels

This function uses the min and max coordinates in the label files of the original LRS data. It is approximate but fast. Below an example to search for tracks crossing a box bounded by longitude and latitudes (over Schrodinger crater):

```bash
tracks = LRS.tracks_intersecting_latlon_box([-80, -70], [110, 155], sampling=100e3)
```