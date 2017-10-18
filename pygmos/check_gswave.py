#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import os
import numpy
try:
    from astropy.io import fits as pyfits
except ImportError:
    import pyfits
import shutil
#from pyraf import iraf
#from iraf import gemini
#from iraf import gmos
#from iraf import images
#from iraf import tv


def main(cluster, mask, logfile, outfile, thresh=0.25):
    """Returns the indices of those slits that went wrong."""
    pathin = os.path.join(cluster, 'mask' + str(mask), logfile)
    outfilename = os.path.join(cluster, 'mask' + str(mask), outfile)
    rms = check(pathin, mask, outfilename)
    over = 0
    wayout = []
    for i in range(len(rms)):
        if rms[i][1] > 0.2:
            over += 1
        if rms[i][1] > thresh:
            wayout.append(i)
    return wayout


def check(path, mask, outfilename):
    fits = []
    log = open(path)
    out = open(outfilename, 'w')
    slit = ''
    for line in log:
        if line[:9] == 'NOAO/IRAF': # to restart after every slit
            median = numpy.median(rms)
            std = numpy.std(rms)
            fits.append([slit, median, std])
            slits.append(median)
            sdev.append(std)
            print(slit, median, '%.4f' %std, file=out)
            slit = ''
        if line[:8] == 'inimages':
            line = line.split()
            image = line[2]
            print(image, file=out)
            slit = ''
            slits = []
            sdev = []
        if line[:3] == 'MDF':
            slit = int(line[9:])
            rms = []

        if slit:
            if line[:18] == '  ' + image:
                line = line.split()
                try:
                    rms.append(float(line[4]))
                except IndexError:
                    if line[3] == 'found':
                        print('No solution found for slit', line[0])
            if line[:16] == image:
                line = line.split()
                rms.append(float(line[6]))
        if line[:17] == 'GSWAVELENGTH exit':
            try:
                print('Mask', mask)
                print(image)
                print('Wavelength calibration RMS (values over all slits, in' \
                      ' Angstrom):')
                print('  median={0:.3f}    min={1:.3f}    max={2:.3f}'.format(
                        numpy.median(slits), min(slits), max(slits)))
                print('  median_std={0:.3f}    min_std={1:.3f}' \
                      '    max_std={2:.3f}'.format(
                        numpy.median(sdev), min(sdev), max(sdev)))
                print('-' * 50)
                print('-' * 50)
            except ValueError:
                pass
    return fits


def Look(image, mask):
    gmos.gdisplay(image, '1')
    good = raw_input('Is everything OK with the wavelength calibrations' \
                     ' for mask {0}? [YES/no]: '.format(mask))
    if good.lower() in ('n', 'no'):
        return False
    return True


def IdentifyBadSlits(image, Nstars):
    linefile = '../../CuAr_GMOS.dat'
    N = getNslits(image)
    bad = []
    print('Introduce the indices of poorly calibrated slits, separated' \
          ' by comma')
    bad_str = raw_input("(press Enter if you don't know).\t")
    if len(bad_str) > 0:
        bad_str = bad_str.split(',')
        for slit in bad_str:
            bad.append(slit)
    else:
        for i in range(1, N + 1):
            tv.display(image + '[sci,' + str(i) + ']', '1')
            is_ok = 'Wavelength calibration for slit {0} OK?' \
                    ' [YES/no]: '.format(i)
            if raw_input(is_ok) == 'no':
                bad.append(i)
    print('#' * 15)
    print('Slits with a bad wavelength calibration:')
    for slit in bad:
        x = int(slit) + Nstars
        print(slit, '-->', end=' ')
        if x >= 10:
            print('_0{0}'.format(x))
        else:
            print('_00{0}'.format(x))
    print('#' * 15)
    return bad


def ReplaceCalibrations(
        image, badslits, Nstars, indir='database2', outdir='database'):
    for slit in badslits:
        x = int(slit) + Nstars
        if x < 10:
            ext = '_00{0}'.format(x)
        else:
            ext = '_0{0}'.format(x)
        infiles = ['id' + image + ext, 'fc' + image + ext]
        for infile in infiles:
            shutil.copyfile(
                os.path.join(indir, infile), os.path.join(outdir, infile))
        print('*' * 15)
        print('Copied database files for slit {0}'.format(slit))
        print('*' * 15)
    return


def getNslits(filename):
    f = pyfits.open('{0}.fits'.format(filename))
    N =  len(f) - 2
    f.close()
    return N


def ManualCheck(lines, verbose=False):
    """Change `pr` for `verbose`"""
    f = open('CuAr_GMOS-ACT.dat')
    skylines = []
    for l in f:
        if l[0] != '#':
            l = l.split()
            skylines.append(float(l[0]))
  
    diff = []
    for line in lines:
        diff.append(100)
        i = len(diff) - 1
        for skyline in skylines:
            if abs(line - skyline) < diff[i]:
                diff[i] = line - skyline

    med = numpy.median(diff)
    std = numpy.std(diff)
    rms = std * numpy.sqrt(len(diff))
    if verbose:
        print(diff)
    print('med = {0:.2f};\tstd = {1:.2f};\trms = {2:.2f} ({3} lines)'.format(
            med, std, rms, len(lines)))
    return med, std, rms


if __name__ == '__main__':
    main()

