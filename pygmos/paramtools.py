from __future__ import absolute_import, division, print_function

import argparse
import sys
from os import environ
from os.path import abspath, dirname, join, split
from pyraf import iraf
#from iraf import gemini
#from iraf import gmos


def dump_file(infile):
    """
    Dump contents of file into output provided in the command line.

    Adapted from
    https://docs.python.org/3/library/argparse.html#action and
    https://goo.gl/BWfK5Y

    """
    class DumpFile(argparse.Action):
        def __call__(self, parser, args, outfile, option_string=None):
            if outfile is None:
                outfile = sys.stdout
            else:
                outfile = open(outfile, 'w')
            with open(infile) as f:
                print(f.read(), file=outfile, end='')
            sys.exit()
    return DumpFile


def read_iraf_params(args):
    """Read IRAF task parameters from IRAF parameter file"""
    with open(args.paramfile) as pfile:
        for line in pfile:
            if line[0] == '@':
                task = getattr(iraf, line.split()[0][1:])
            if '=' in line and line[0] != '#':
                # just in case, so that splitting by spaces works
                line = line.replace('=', ' = ')
                line = line.split()
                if len(line) > 2 and line[2] != '#':
                    task.setParam(
                        line[0], line[2].replace(
                            'pygmos$',
                            '{0}/'.format(environ['pygmos_path'])))
                else:
                    task.setParam(line[0], '')
    return


def read_args():
    """Wrapper to parse and customize command-line arguments"""
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
    add('-i', '--inventory', dest='inventory_only', action='store_true',
        help='Only run the inventory for a given object, without actually' \
             ' reducing the data')
    add('-m', '--masks', dest='masks', nargs='*', default='all',
        help='Which MOS masks to reduce (identified by their numbers),' \
             ' or "longslit" if you are going to reduce longslit' \
             ' observations.')
    add('-n', '--nod-shuffle', dest='nod', action='store_true',
        help='Set if reducing nod & shuffle observations' \
             ' (NOT YET IMPLEMENTED)')
    add('--no-ds9', dest='ds9', action='store_false',
        help='Do not start a ds9 session to display files as they are' \
             ' created')
    add('-p', '--param-file', dest='paramfile',
        default=join(environ['pygmos_path'], 'pygmos.param'),
        help='File containing IRAF parameter definitions')
    add('--path', dest='path', default='./',
        help='path to raw GMOS files')
    add('--program', dest='program', default='',
        help='Gemini Program ID')
    add('-r', '--read-inventory', dest='read_inventory', action='store_true',
        help='Read an already-existing inventory file instead of producing' \
             ' one')

    # dump files
    add('-d', dest='dump_file', nargs='?', default=None,
        help='Dump a sample parameter file to the console or to a file',
        action=dump_file(join(environ['pygmos_path'], 'docs',
                              'pygmos.params')))
    add('-dd', dest='dump_file_extended', nargs='?', default=None,
        help='Dump an extended parameter file to the console or to a file',
        action=dump_file(join(environ['pygmos_path'],
                              'docs', 'pygmos.params.extended')))

    return parser


def setup_args(parser):
    """Any manipulation of the arguments that may be required"""
    args = parser.parse_args()
    if args.nod:
        print('\nSorry, reduction of nod & shuffle observations' \
              ' is not supported at the moment. Exiting pygmos.\n\n')
        sys.exit()
    return args



# for testing purposes
if __name__ == '__main__':
    read_args()



