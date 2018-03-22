from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import os
import six
import sys
from glob import glob
try:
    from astropy.io import fits as pyfits
except ImportError:
    import pyfits

if sys.version_info[0] == 3:
    basestring = str


intro = """

------------------------------------------------------------------------
------------------------------------------------------------------------

          ################################################
          #                                              #
          #                    PyGMOS:                   #
          #                                              #
          #  PyRAF-GMOS reduction pipeline developed by  #
          #                Cristobal Sifon               #
          #                                              #
          #               current address:               #
          #   Princeton University, Princeton, NJ, USA   #
          #           sifon@astro.princeton.edu          #
          #                                              #
          #   https://github.com/cristobal-sifon/pygmos  #
          #                                              #
          # -------------------------------------------- #
          #                                              #
          #           Last Updated October, 2017         #
          #                                              #
          ################################################

------------------------------------------------------------------------
------------------------------------------------------------------------

"""

def add_prefix(filename, task):
    outpref = (task if isinstance(task, six.string_types) else task.outpref)
    tree = filename.split('/')
    #tree[-1] = task.outpref + tree[-1]
    tree[-1] = outpref + tree[-1]
    return os.path.join(*tree)


def get_science_files(assocfile, mask):
    file = open(assocfile)
    head = '#'
    while head[0] == '#':
        head = file.readline()
    head = head.split()
    scol = head.index('Science')
    mcol = head.index('Mask')
    science = {}
    for line in file:
        if line[0] == '#':
            continue
        line = line.split()
        if len(line) >= 7:
            if line[mcol] == mask:
                science[line[scol]] = int(line[2])
    return science


def get_darks():
    darks = []
    for ls in glob('*.fits'):
        head = pyfits.getheader(ls)
        if head['OBSTYPE'] == 'DARK':
            darks.append(ls[:-5])
    return ','.join(darks)


def get_wavelengths(assocfile):
    file = open(assocfile)
    head = '#'
    while head[0] == '#':
        head = file.readline()
    head = head.split()
    wavecol = head.index('Wave')
    waves = []
    for line in file:
        if line[0] != '#':
            line = line.split()
            w = int(line[wavecol])
            if not w in waves:
                waves.append(w)
    return waves


def copy_MDF(science, cluster, mask):
    head = pyfits.open(science + '.fits')[0].header
    mdffile = head['MASKNAME']
    targetdir = cluster.replace(' ', '_') + '/mask' + mask + '/'
    if not os.path.isfile(targetdir):
        os.system('cp -p {0}.fits {1}'.format(mdffile, targetdir))
    return


def delete(filename):
    ls = glob(filename)
    for filename in ls:
        os.remove(filename)
    return


def skip(args, task_name, task_output):
    """Check whether a task should be skipped based on `args.begin`"""
    tasks = ['gradimage', 'flat', 'reduce', 'lacos', 'wavelength', 'transform',
             'skysub', 'combine', 'extract']
    i = tasks.index(task_name)
    if not task_output.endswith('.fits'):
        task_output = '{0}.fits'.format(task_output)
    if os.path.isfile(task_output) and args.begin in tasks[i+1:]:
        return True
    return False


def get_nslits(filename):
    f = pyfits.open('{0}.fits'.format(filename))
    N =  len(f) - 2
    f.close()
    return N


def get_nstars(filename):
    fits = pyfits.open(filename + '.fits')
    data = fits[1].data
    N = 0
    priority = data.field('priority')
    for slit in priority:
        if slit == '0':
            N += 1
    fits.close()
    return N


def makedir(name):
    if not os.path.isdir(name):
        os.makedirs(name)
    return


def read_key(fitsfile, key):
    head = pyfits.getheader(fitsfile + '.fits')
    try:
        value = head[key]
    except KeyError:
        return
    return value


def remove_previous_files(name, filetype=''):
    """Mainly for the flat files"""
    delete('g{0}.fits'.format(name))
    delete('gs{0}.fits'.format(name))
    if filetype == 'flat':
        delete('{0}_flat.fits'.format(name))
        delete('{0}_comb.fits'.format(name))
    return


def removedir(dirname):
    try:
        os.rmdir(dirname)
    except OSError:
        try:
            os.chdir(dirname)
        except OSError: # Means that the folder doesn't exist
            return
        os.system('rm *')
        os.chdir('..')
        os.rmdir(dirname)
    return


def write_offsets(inimages, output):
    xoffset = []
    yoffset = []
    for img in inimages:
        head = pyfits.getheader(img)
        xoffset.append(head['XOFFSET'])
        yoffset.append(head['YOFFSET'])
    out = open(output, 'w')
    for i in range(len(xoffset)):
        print(xoffset[i], '\t', yoffset[i], file=out)
    return output




