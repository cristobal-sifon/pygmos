# -*- coding: utf-8 -*-
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from glob import glob
import os
import sys
try:
    from astropy.io.fits import getheader
except ImportError:
    from pyfits import getheader


def assoc(cluster, program, bias, path='./', verbose=True):
    files = sorted(glob(os.path.join(path, '*.fits*')))
    print('Found {0} FITS files in {1}'.format(len(files), path))
    exp, masks = find_masks(files, cluster, program, bias)
    exp = find_exposures(files, exp)
    # did we find the object?
    msg = 'object {0} not found. Make sure you have defined the path' \
          ' correctly (type `pygmos -h` for help).'.format(cluster)
    assert len(exp) > 0, msg
    # print file information to file
    print_assoc(cluster, exp, bias, verbose=verbose)
    return masks


def generate(program, cluster, bias, path='./', verbose=True):
    if verbose:
        print('#-' * 20 + '#')
        print(' Making inventory for object', cluster)
        print('#-' * 20 + '#\n')
    masks = assoc(cluster, program, bias, path)
    if verbose:
        print()
        print('#-' * 20 + '#')
        print(' Inventory ready. Look for "{0}.assoc"'.format(cluster))
        print('#-' * 20 + '#')
    return masks


def read(cluster, bias, col=1):
    masks = []
    with open('{0}.assoc'.format(cluster)) as f:
        line = f.readline()
        if line[0] == '#':
            line = line.split()
            m = int(line[col])
            if m not in masks:
                masks.append(m)
                #os.chdir(os.path.join(cluster, 'mask{0}'.format(m)))
                #os.system('ln -sf ../../{0}* .'.format(bias))
            #for i in range(4, 7):
                #os.system('ln -sf ../../{0}.fits* .'.format(line[i]))
        #os.chdir('../..')
    return masks


def find_masks(files, cluster, program, bias):
    """Identify available masks and wavelength configurations"""
    masks = []
    exp = []
    for filename in files:
        head = getheader(filename)
        # is this a Gemini observation?
        if 'GEMPRGID' not in head:
            continue
        # is it a spectroscopic observation?
        if 'MASKNAME' not in head or head['MASKNAME'] == 'None':
            continue
        # is it from the right observing program?
        if program and program != head['GEMPRGID']:
            continue
        # is it the right observing class?
        if head['OBSCLASS'] != 'science':
            continue
        # finally, is it the right object?
        if head['OBJECT'].replace(' ', '_') == cluster:
            obsid = head['OBSID']
            wave = head['CENTWAVE']
            exptime = int(head['EXPTIME'])
            if 'arcsec' in head['MASKNAME']:
                mask = head['MASKNAME']
                newdir = mask
            elif head['MASKNAME'][:2] in ('GN','GS'):
                mask = int(head['MASKNAME'][-2:])
                newdir = 'mask{0}'.format(mask)
            if [obsid, mask, wave, exptime] not in exp:
                if mask not in masks:
                    newdir = os.path.join(cluster, newdir)
                    makedir(newdir)
                    masks.append(mask)
                exp.append([obsid, mask, wave, exptime])
    return exp, masks


def find_exposures(files, exp):
    Nexp = len(exp)
    """Identify files corresponding to each mask"""
    info = []
    for filename in files:
        head = getheader(filename)
        try:
            for i in range(Nexp):
                # the int(maskname) here works for MOS only
                try:
                    if float(head['CENTWAVE']) == exp[i][2] and \
                            int(head['MASKNAME'][-2:]) == exp[i][1]:
                        obsID = exp[i][0]
                        wave  = exp[i][2]
                        mask  = exp[i][1]
                        info.append(
                            [filename[:filename.index('.fits')],
                             obsID, mask, head['OBSTYPE'], wave])
                except ValueError:
                    pass
        except KeyError:
            pass
    # this is where the filenames will be stored
    for i in range(Nexp):
        for j in range(3):
            exp[i].append('')
    # only takes one flat and one arc per mask+wavelength for now.
    for i in range(Nexp):
        for j in range(len(info)):
            if exp[i][0] == info[j][1] and exp[i][2] == info[j][4]:
                if info[j][3] == 'OBJECT':
                    exp[i][4] = info[j][0]
                if info[j][3] == 'FLAT':
                    exp[i][5] = info[j][0]
                if info[j][3] == 'ARC':
                    exp[i][6] = info[j][0]
    return exp


def print_assoc(cluster, exp, bias, verbose=True):
    output = '{0}.assoc'.format(cluster)
    out = open(output, 'w')
    head = 'ObservationID\t\tMask\tWave\t Time\t\tScience\t\tFlat\t\tArc'
    print(head, file=out)
    if verbose:
        print(head)

    for i in range(len(exp)):
        msg = '{0}  \t{1:2d}\t{2}\t{3:5d}\t\t{4}\t{5}\t{6}'.format(
                exp[i][0], exp[i][1], int(10*exp[i][2]),
                exp[i][3], exp[i][4], exp[i][5], exp[i][6])
        print(msg, file=out)
        if verbose:
            print(msg)
        science = exp[i][4] + '.fits'
        flat = exp[i][5] + '.fits'
        arc = exp[i][6] + '.fits'
        os.chdir(os.path.join(cluster, 'mask{0}'.format(exp[i][1])))
        os.system('ln -sf ../../' + science + '* .')
        os.system('ln -sf ../../' + flat + '* .')
        os.system('ln -sf ../../' + arc + '* .')
        if bias:
            os.system('ln -sf ../../' + bias + '* .')
        os.chdir('../../')
    return output



def makedir(name):
    if not os.path.isdir(name):
        os.makedirs(name)
    return



