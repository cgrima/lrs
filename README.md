# LRS
Tools for manipulating Lunar Radar Sounder (LRS) data from the JAXA's Kaguya 
spacecraft. Data available at [JAXA's Data ARchives and Transmission System (DARTS) ](https://darts.isas.jaxa.jp/planet/pdap/selene/index.html.en).

## Working Directory

The hierarchy of the working directory is assumed to be 

```bash
./code/
    lrs/ # This repository
./data/
    orig/
        sln-l-lrs-5-sndr-ss-sar05-power-v1.0/
        sln-l-lrs-5-sndr-ss-sar10-power-v1.0/
        [...]
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

### Basic Data Info from Label Files

Create an instance that will hold basic information about the LRS dataset.
By default, any python command is assumed to be launched from within
the `./code` directory. If note, please change the keyword `root_path`.

```bash
# Initiate instance
LRS = lrs.Classdef.Env(root_path='../')
```

Basic request from data within the label files:

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
