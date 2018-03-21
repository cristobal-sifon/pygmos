#! /usr/bin/env python
#    2016-Jun-08  shaw@noao.edu
from __future__ import print_function

import sys
from pyraf import iraf
from pyraf.iraf import gemini, gemtools, gmos
import fileSelect as fs

def gmos_img_proc():
    '''
    GMOS Data Reduction Cookbook companion script to the chapter:
      "Reduction of Images with PyRAF"

    PyRAF script to:
    Process GMOS images for Messier 8, in program GS-2006B-Q-18.

    The names for the relevant header keywords and their expected values are
    described in the Cookbook chapter entitled "Supplementary Material"

    Perform the following starting in the parent work directory:
      cd /path/to/work_directory

    Fetch the Static BPM file from the tutorial, place it in your work
    directory,
    and uncompress:
       bpm_gmos-s_EEV_v1_2x2_img_MEF.fits

    Place the fileSelect.py module in your work directory. 
    You may cut-n-paste lines from this script to your pyraf session, or 
    from the unix prompt: 
       python gmos_img_proc.py
    '''

    print("### Begin Processing GMOS/MOS Images ###")
    print("###")
    print("=== Creating MasterCals ===")

    # This whole example depends upon first having built an sqlite3
    # database of metadata:
    #    cd ./raw
    #    python obslog.py obsLog.sqlite3
    dbFile='./raw/obsLog.sqlite3'

    # From the work_directory:
    # Create the query dictionary of essential parameter=value pairs.
    # Select bias exposures within ~2 months of the target observations:
    qd = {'use_me':1,
          'Instrument':'GMOS-S','CcdBin':'2 2','RoI':'Full','Object':'M8-%',
          'DateObs':'2006-09-01:2006-10-30'
          }
    print(" --Creating Bias MasterCal--")

    # Set the task parameters.
    gmos.gbias.unlearn()
    biasFlags = {
        'logfile':'biasLog.txt','rawpath':'./raw/','fl_vardq':'yes',
        'verbose':'no'
    }
    # The following SQL generates the list of files to process.
    SQL = fs.createQuery('bias', qd)
    biasFiles = fs.fileListQuery(dbFile, SQL, qd)
    
    # The str.join() funciton is needed to transform a python list into
    # a string filelist that IRAF can understand.
    if len(biasFiles) > 1:
        gmos.gbias(','.join(str(x) for x in biasFiles), 'MCbias.fits',
            **biasFlags)

    # Clean up
    iraf.imdel('gS2006*.fits')

    print(" --Creating Twilight Imaging Flat-Field MasterCal--")
    # Select flats obtained contemporaneously with the observations.
    qd.update({'DateObs':'2006-09-10:2006-10-10'})

    # Set the task parameters.
    gmos.giflat.unlearn()
    flatFlags = {
        'fl_scale':'yes','sctype':'mean','fl_vardq':'yes',
        'rawpath':'./raw/','logfile':'giflatLog.txt','verbose':'no'
        }
    filters = ['Ha', 'HaC', 'SII', 'r', 'i']
    for f in filters:
        print("  Building twilight flat MasterCal for: {}".format(f))

        # Select filter name using a substring of the official designation.
        qd['Filter2'] = f + '_G%'
        mcName = 'MCflat_%s.fits' % (f)
        flatFiles = fs.fileListQuery(dbFile, fs.createQuery('twiFlat', qd), qd)
        if len(flatFiles) > 0:
            gmos.giflat(','.join(str(x) for x in flatFiles), mcName, 
                         bias='MCbias', **flatFlags)

    iraf.imdel('gS2006*.fits,rgS2006*.fits')

    print("=== Processing Science Images ===")
    # Remove restriction on date range
    qd['DateObs'] = '*'
    prefix = 'rg'

    # Set task parameters.
    # Employ the imaging Static BPM for this set of detectors.
    gmos.gireduce.unlearn()
    sciFlags = {
        'fl_over': 'yes', 'fl_trim': 'yes', 'fl_bias': 'yes', 'fl_dark': 'no',
        'fl_flat': 'yes', 'logfile': 'gireduceLog.txt', 'rawpath': './raw/',
        'fl_vardq': 'yes', 'bpm': 'bpm_gmos-s_EEV_v1_2x2_img_MEF.fits',
        'verbose': 'no'}
    gemtools.gemextn.unlearn()    # disarms a bug in gmosaic
    gmos.gmosaic.unlearn()
    mosaicFlags = {
        'fl_paste': 'no', 'fl_fixpix': 'no', 'fl_clean': 'yes',
        'geointer': 'nearest','logfile': 'gmosaicLog.txt', 'fl_vardq': 'yes',
        'fl_fulldq': 'yes', 'verbose': 'no'}
    # Reduce the science images, then mosaic the extensions in a loop
    for f in filters:
        print("    Processing science images for: {}".format(f))
        qd['Filter2'] = f + '_G%'
        flatFile = 'MCflat_' + f + '.fits'
        sciFiles = fs.fileListQuery(dbFile, fs.createQuery('sciImg', qd), qd)
        if len(sciFiles) > 0:
            gmos.gireduce (','.join(str(x) for x in sciFiles), bias='MCbias',
                           flat1=flatFile, **sciFlags)
            for file in sciFiles:
                gmos.gmosaic (prefix+file, **mosaicFlags)

    iraf.imdelete('gS2006*.fits,rgS2006*.fits')

    ## Co-add the images, per position and filter.
    print(" -- Begin image co-addition --")

    # Use primarily the default task parameters.
    gemtools.imcoadd.unlearn()
    coaddFlags = {
        'fwhm':3,'datamax':6.e4,'geointer':'nearest','logfile':'imcoaddLog.txt'
        }
    targets = ['M8-1', 'M8-2', 'M8-3']
    prefix = 'mrg'
    for f in filters:
        print("  - Co-addding science images in filter: {}".format(f))
        qd['Filter2'] = f + '_G%'
        for t in targets:
            qd['Object'] = t + '%'
            print("  - Co-addding science images for position: {}".format(t))
            outImage = t + '_' + f + '.fits'
            coAddFiles = fs.fileListQuery(dbFile, fs.createQuery('sciImg', qd), qd)
            gemtools.imcoadd(','.join(prefix+str(x) for x in coAddFiles),
                    outimage=outImage, **coaddFlags)

    iraf.delete ("*_trn*,*_pos,*_cen")
    iraf.imdelete ("*badpix.pl,*_med.fits,*_mag.fits")
    #iraf.imdelete ("mrgS*.fits")

    print("=== Finished Calibration Processing ===")

if __name__ == "__main__":
    gmos_img_proc()

