# -*- coding: utf-8 -*-
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import logging
import os
import sys
try:
    from astropy.io.fits import getheader
except ImportError:
    from pyfits import getheader
from glob import glob

from ..utilities import utils

import numpy as np
from astropy.table import Table

logger = logging.getLogger(__name__)


def assoc(target, program, bias, path='./', verbose=True):
    files = sorted(glob(os.path.join(path, '*.fits*')))
    print('Found {0} FITS files in {1}\n'.format(len(files), path))
    exp, masks = find_masks(files, target, program, bias)
    # did we find the object?
    msg = 'object {0} not found. Make sure you have defined the path' \
          ' correctly (type `pygmos -h` for help).'.format(target)
    assert len(exp.keys()) > 0, msg
    for obj in exp:
        exp[obj] = find_exposures(files, exp[obj])
        # print file information to file
        assoc_file = print_assoc(obj, exp[obj], bias, verbose=verbose)
    return masks, assoc_file


def find_masks(files, target, program, bias):
    """Identify available masks and wavelength configurations"""
    # auxiliary
    if target == 'inventory':
        search_targets = True
    else:
        search_targets = False
    masks = {}
    exp = {}
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
        obj = head['OBJECT']
        if target == 'inventory' or obj == target:
            obsid = head['OBSID']
            wave = head['CENTWAVE']
            exptime = int(head['EXPTIME'])
            mask = head['MASKNAME']
            newdir = mask
            if obj not in masks:
                masks[obj] = []
                exp[obj] = []
            if [obsid, mask, wave, exptime] not in exp[obj]:
                if mask not in masks[obj]:
                    newdir = os.path.join(obj, newdir).replace(' ', '_')
                    utils.makedir(newdir)
                    masks[obj].append(mask)
                exp[obj].append([obsid, mask, wave, exptime])
    # `masks` are no longer used within the inventory
    # except to pass them to the main program for data reduction
    if target != 'inventory':
        try:
            masks = masks[target]
        except KeyError:
            msg = 'No files found for object {0}.\n'.format(target)
            logger.error(msg)
            raise
    return exp, masks


def find_exposures(files, exp):
    Nexp = len(exp)
    """Identify files corresponding to each mask"""
    info = []
    for filename in files:
        head = getheader(filename)
        # is this a Gemini observation?
        if 'CENTWAVE' in head and 'MASKNAME' in head and 'OBSTYPE' in head:
            for i in range(Nexp):
               if float(head['CENTWAVE']) == exp[i][2] \
                        and head['MASKNAME'] == exp[i][1]:
                    obsID = exp[i][0]
                    wave  = exp[i][2]
                    mask  = exp[i][1]
                    info.append(
                        [filename[:filename.index('.fits')],
                         obsID, mask, head['OBSTYPE'], wave])

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


def generate(args, program, target, bias, path='./', verbose=True):
    if verbose:
        print('#-' * 20 + '#')
        if target == 'inventory':
            print('Finding and inventorying all objects in {0}'.format(path))
        else:
            print(' Making inventory for object', target)
        print('#-' * 20 + '#\n')
    # will fix later
    bias = args.bias
    masks, assoc_file = assoc(target, program, bias, path)
    if verbose:
        print()
        print('#-' * 20 + '#')
        if target == 'inventory':
            print('Inventory ready. Look for *.assoc files')
        else:
            print(' Inventory ready. Look for "{0}.assoc"'.format(assoc_file))
        print('#-' * 20 + '#')
    return masks


def print_assoc(obj, exp, bias, verbose=True):
    output = '{0}.assoc'.format(obj.replace(' ', '_'))
    print('{0}\n-----'.format(output))
    out = open(output, 'w')
    head = '{0:<16s}  {1:<15s}  {2:<5s}  {3:<5s}' \
           '  {4:<14s}  {5:<14s}  {6:<14s}'.format(
               'ObservationID', 'Mask', 'Wave', 'Time', 'Science', 'Flat',
               'Arc')
    print(head, file=out)
    if verbose:
        print(head)

    for i in range(len(exp)):
        msg = '{0}  {1:<14s}  {2:5d}  {3:5d}  {4:<14s}  {5:<14s}' \
              '  {6:<14s}'.format(
                exp[i][0], exp[i][1], int(10*exp[i][2]),
                exp[i][3], exp[i][4].split('/')[-1],
                exp[i][5].split('/')[-1], exp[i][6].split('/')[-1])
        print(msg, file=out)
        if verbose:
            print(msg)
        science = exp[i][4] + '.fits'
        flat = exp[i][5] + '.fits'
        arc = exp[i][6] + '.fits'
        # just for clarity
        mask = exp[i][1]
        os.chdir(os.path.join(obj, mask).replace(' ', '_'))
        # copy MOS mask definition file
        if mask[:2] in ('GN', 'GS'):
            os.system('ln -sf ../../{0}.fits .'.format(mask))
        for file in (science, flat, arc):
            os.system('ln -sf ../../{0}* .'.format(file))
        if bias:
            os.system('ln -sf ../../{0}* .'.format(bias))
        os.chdir('../../')
    if verbose:
        print()
    return output


def read(target, bias, col=1):
    masks = []
    with open('{0}.assoc'.format(target.replace(' ', '_'))) as f:
        for line in f:
            print(line)
            if line[0] == '#' or line[:13] == 'ObservationID':
                continue
            line = line.split()
            if len(line) == 0:
                continue
            print(line[col])
            if line[col] not in masks:
                masks.append(line[col])
    return masks


def run(args):
    """Main inventory routine."""
    # longslit observations
    if args.masks == 'longslit':
        masks = generate(
            args, args.program, args.objectid, args.bias,
            args.path, masktype=args.masks)

    # just read masks from pre-existing assoc files
    elif args.read_inventory:
        masks = read(args.objectid, args.bias)

    # all MOS masks
    elif args.masks == 'all':
        masks = generate(
            args, '', args.objectid, args.bias, args.path)

    # when MOS masks are specified
    else:
        masks = generate(
            args, args.program, args.objectid, args.bias, args.path)

    return masks


def get_file_longslit(assoc, obs='science', wave=670):
    """
    Select rows in the association file that contain 
    the type of observation of interest for the central
    wavelength setup of choice.
    """
    data = Table.read(assoc, format='ascii')
    return np.array(data[data['Wave']==wave][str.capitalize(obs)])


def get_file(assoc, science, mask=1, obs='science', wave=670):
    """
    !!! As called in other parts of the code, this function 
    will only work for the MOS track, not the longslit functionality
    of the code.
    """
    assocfile = open(assoc)
    while assocfile.readline()[0] == '#':
        pass
    for line in assocfile:
        if line[0] == '#':
            continue
        line = line.split()
        if len(line) < 7:
            continue
        if mask == 'longslit':
            if int(line[2]) == wave and line[4] == science:
                if obs == 'science':
                    return line[4]
                if obs == 'flat':
                    return line[5]
                if obs == 'arc' or obs == 'lamp':
                    return line[6]
                else:
                    print('Unknown observation type in get_file(). Exiting')
                    sys.exit()
        elif line[1] == mask and int(line[2]) == wave and line[4] == science:
                if obs == 'science':
                    return line[4]
                if obs == 'flat':
                    return line[5]
                if obs == 'arc' or obs == 'lamp':
                    return line[6]
                else:
                    print('Unknown observation type in get_file(). Exiting')
                    sys.exit()
    return
