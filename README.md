# LRS
Tools for manipulating Lunar Radar Sounder (LRS) data from the JAXA's Kaguya 
spacecraft. Data available at [JAXA's Data ARchives and Transmission System (DARTS) ](https://darts.isas.jaxa.jp/planet/pdap/selene/index.html.en).


## Working Directory

Create a `code` folder in your working directory and clone this repository inside. In a terminal:

```bash
mkdir code
cd code
git clone git@github.com:cgrima/lrs.git
```

From now on, the code will automatically build the hierarchy with the data. It will look like below. To start, just proceed to the next section **Initilisation**.

```bash
./code/
    lrs/ # Clone of this repository
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


## Initialisation

Launch a python instance from within the `./code` folder.

Optionally, set first your logging level to `INFO` in order to see info messages.

```python
import logging
logger = logging.getLogger().setLevel(logging.INFO)
```

Then, create an instance (i.e., Class) that will hold basic information about the LRS dataset.
By default, any python command is assumed to be launched from within
the `./code` directory. If note, please change the keyword `root_path` in `lrs.Classdev.Env()`.

```python
# Initiate instance
import lrs
LRS = lrs.Classdef.Env()
```

If the `data/` folder does not exist, it will be automatically created. There is no data files neither, so the the command `LRS.files` should return an empty array.


## Data Download

### With the built-in python function

Once the LRS Class is loaded (see above), you can download data for a given product and track. The `typ` keyword let's choos whether you want to download the `lbl` or `img` file. For example:

```bash
_ = LRS.download('sln-l-lrs-5-sndr-ss-sar40-power-v1.0', '20071219231328', typ='lbl')
_ = LRS.download('sln-l-lrs-5-sndr-ss-sar40-power-v1.0', '20071219231328', typ='img')
```

For the code to integrate your dowloaded file, re-initialize the LRS Class:

```python
LRS = lrs.Classdef.Env()
```

It should tell you that there is 1 track available.

The repository has a `tracks.csv` file with all the identifiers of tracks available on the JAXA server. You can use this file to batch download the data and populate your hierarchy. For example:

```python
# Open tracks.csv
tracks = np.loadtxt('lrs/tracks.csv', delimiter=",", dtype=str)

# Batch download only the lbl files from the sar05 products:
for track in tracks:
    if track[0] = 'sln-l-lrs-5-sndr-ss-sar05-power-v1.0':
        _ = LRS.download(track[0], track[1], typ='lbl') 
```


### [Optional] From the terminal (using lftp)

To download data from a given processing mode (e.g. 
`sln-l-lrs-5-sndr-ss-sar05-power-v1.0`), but without `*.img` and `*.jpg` files
to download the data hierarchy without the largest files (`man lftp` for additional options):

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


## Basic Data Info from Label Files

Basic requests from data within the label files:

```python
# Get available file names
LRS.files['sln-l-lrs-5-sndr-ss-sar40-power-v1.0']['20071219231328']
>> ['../data/orig/sln-l-lrs-5-sndr-ss-sar40-power-v1.0/20071219/data/LRS_SAR40KM_20071219231328.lbl']

# Get start and stop latitude
LRS.lat_lim('sln-l-lrs-5-sndr-ss-sar40-power-v1.0', '20071219231328')
>> [-35.961, 75.148]

# Get start and stop spacecraft clock time
LRS.clock_lim('sln-l-lrs-5-sndr-ss-sar40-power-v1.0', '20071219231328')
>> [882141206, 882143419]
```

## Load Original Data

To load original data from a track in a friendly format:

```python
# Load original data
data = LRS.orig_data['sln-l-lrs-5-sndr-ss-sar05-power-v1.0']['20071221033918']

# The function above also accepts any matching substrings for the product, e.g.
data = LRS.orig_data['sar05']['20071221033918']

# Display keys contained in the data
data.keys()
>> dict_keys(['OBSERVATION_TIME', 'DELAY', 'START_STEP', 'SUB_SPACECRAFT_LATITUDE', 'SUB_SPACECRAFT_LONGITUDE', 'SPACECRAFT_ALTITUDE', 'DISTANCE_TO_RANGE0', 'TI', 'IMG'])
```


## Processings

The `./data/lrs/xtra/` folder will store derived data product created by various processings, and with the same hierarchy as in the `orig` directory. 

### Auxiliary Data

Auxilliary data (e.g., latitude, longitude...) can be obtained by loading the original `.img` file as explained in the former section. However, the original data also contains the radargram, which can take a lot of memory. The auxiliary files are like the orig files but without the radargram, so that it is much lighter to load.

> `aux` files are used by many functions in this repository. Make sure to create those files first before attempting other processings.

To extract and archive auxiliary data from the header of the LRS orig files. 

```python
_ = LRS.run('aux', 'sar05', '20071221033918', archive=True, delete=True)
```

### Surface Echo

To get the surface echo coordinate and power
```python
srf = lrs.processing.srf(data, method='mouginot2010')
```

The default surface picking method is from Mouginot et al. (2010). Using the one from Grima et al. (2012) is also possible, but it seems to pick the off-nadir echo mor often. However, Mouginot et al. (2010) is more sensitive to an earlier continuous artifact as illustrated below

```python
product = 'sln-l-lrs-5-sndr-ss-sar05-power-v1.0'
name = '20071221093226'
latlim = [10, 20]

img, idx = LRS.plt_rdg(product, name, latlim=latlim, cmap='gray_r', vmin=-10, vmax=40)

srf = lrs.processing.srf(data, method='grima2012')
plt.plot(srf['y'], label='[Grima et al., 2012]')

srf = lrs.processing.srf(data, method='mouginot2010')
plt.plot(srf['y'], label='[Mouginot et al., 2010]')

plt.legend()
```

![Plot](./images/surface_picking.png?raw=true)

### Batch processing

To run a processing on all the available data using 8 cores in parallel

```python
LRS.run_all('aux', 'sar05', delete=False, n_jobs=8)
```



## Plot a radargram

The repository provides a limited function to plot a radargram:

```python
product = 'sln-l-lrs-5-sndr-ss-sar05-power-v1.0'
name = '20071221033918'

img = LRS.plt_rdg(product, name, latlim=[-80, -70], cmap='gray_r', vmin=-10, vmax=40)
```
![Plot](./images/plt_rdg.png?raw=true)


## Geographic Query

### From Orig Labels

This function uses the min and max coordinates in the label files of the original LRS data. It is approximate but fast. Below an example to search for tracks crossing a box bounded by longitude and latitudes (over Schrodinger crater)

```python
tracks = LRS.tracks_intersecting_latlon_box([-81, -68], [105, 160], sampling=100e3)
```