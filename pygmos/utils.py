from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import os
import sys
from glob import glob
try:
    from astropy.io import fits as pyfits
except ImportError:
    import pyfits


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


def getScienceFiles(assocfile, mask):
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


def getDarks():
    darks = []
    for ls in glob('*.fits'):
        head = pyfits.getheader(ls)
        if head['OBSTYPE'] == 'DARK':
            darks.append(ls[:-5])
    return ','.join(darks)


def getWavelengths(assocfile):
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


def Copy_MDF(science, cluster, mask):
    head = pyfits.open(science + '.fits')[0].header
    mdffile = head['MASKNAME']
    targetdir = cluster.replace(' ', '_') + '/mask' + mask + '/'
    if not os.path.isfile(targetdir):
        os.system('cp -p {0}.fits {1}'.format(mdffile, targetdir))
    return


def RemovePreviousFiles(name, filetype=''):
    """Mainly for the flat files"""
    delete('g{0}.fits'.format(name))
    delete('gs{0}.fits'.format(name))
    if filetype == 'flat':
        delete('{0}_flat.fits'.format(name))
        delete('{0}_comb.fits'.format(name))
    return


def getFile(assoc, science, mask=1, obs='science', wave=670):
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
                    print('Unknown observation type in getFile(). Exiting')
                    sys.exit()
        else:
            if int(line[1]) == mask and \
                    int(line[2]) == wave and \
                    line[4] == science:
                if obs == 'science':
                    return line[4]
                if obs == 'flat':
                    return line[5]
                if obs == 'arc' or obs == 'lamp':
                    return line[6]
                else:
                    print('Unknown observation type in getFile(). Exiting')
                    sys.exit()
    return


def getNslits(filename):
    f = pyfits.open('{0}.fits'.format(filename))
    N =  len(f) - 2
    f.close()
    return N


def getNstars(filename):
    fits = pyfits.open(filename + '.fits')
    data = fits[1].data
    N = 0
    priority = data.field('priority')
    for slit in priority:
        if slit == '0':
            N += 1
    fits.close()
    return N


def ReadKey(fitsfile, key):
    head = pyfits.getheader(fitsfile + '.fits')
    try:
        value = head[key]
    except KeyError:
        return
    return value


def delete(filename):
    ls = glob(filename)
    for filename in ls:
        os.system('rm %s' %filename)
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


def makedir(dirname, overwrite='yes'):
    dirs = dirname.split('/')
    for i in range(len(dirs)):
        try:
            os.mkdir(dirs[i])
        except OSError:
            if overwrite == 'no':
                pass
        else:
            os.system('rm -r ' + dirs[i])
            os.mkdir(dirs[i])
        os.chdir(dirs[i])
    for i in range(len(dirs)):
        os.chdir('../')
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




