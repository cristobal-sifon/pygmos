from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import argparse
import sys
from os.path import join
from pyraf import iraf
from iraf import gemini
from iraf import gmos


def read_args():
    parser = parse_args()
    args = setup_args(parser)
    return args


def parse_args():
    """Define and read arguments expected from command line"""
    parser = argparse.ArgumentParser(
        description='PyGMOS - A Python/PyRAF data reduction pipeline' \
                    ' for Gemini/GMOS spectroscopic data')
    add = parser.add_argument
    # mandatory arguments
    add('objectid',
        help='Object name as given in the FITS file header. If the' \
             ' object name contains spaces, replace them by' \
             ' underscores ("_").')
    # optional arguments
    add('--align', dest='align', action='store_true',
        help='Produce a FITS file with spectra aligned by wavelength')
    add('--cut-dir', dest='cutdir', default='spectra',
        help='Directory into which the individual 1d spectra will be saved' \
             ' (if --no-cut has not been set)')
    add('-m', '--masks', dest='masks', nargs='*', default=['all'],
        help='Which masks to reduce (identified by their numbers)')
    add('-p', '--param-file', dest='paramfile', default='pygmos.param',
        help='File containing IRAF parameter definitions')
    add('--program', dest='program', default='',
        help='Gemini Program ID')
    return args


def setup_args(parser):
    """Any manipulation of the arguments that may be required"""
    args = parser.parse_args()
    return args


def read_iraf_params(args):
    pfile = open(paramfile)
    for line in pfile:
        if line[0] == '@':
            task = line.split()[0][1:]
            task = getattr(iraf, task)
        if '=' in line and line[0] != '#':
            line = line.split()
            try:
                if line[2] == '#':
                    task.setParam(line[0], '')
                else:
                    task.setParam(line[0], line[2])
            except IndexError:
                task.setParam(line[0], '')
    if gmos.gswavelength.coordlist[0] not in ('/','$') and \
            gmos.gswavelength.coordlist[:2] != '{$' and \
            gmos.gswavelength.coordlist[:6] != '../../':
        gmos.gswavelength.coordlist = join(
            '..', '..', gmos.gswavelength.coordlist)
    return

