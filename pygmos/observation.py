from __future__ import absolute_import, division, print_function

from astropy.io import fits
from astropy.wcs import WCS
from matplotlib import pyplot as plt
import sys


class BaseMaskHeader(object):

    def __init__(self, file):
        self.file = file
        self._header = None

    @property
    def header(self):
        if self._header is None:
            hdr = []
            while True:
                try:
                    hdr.append(fits.getheader(self.file, ext=len(hdr)))
                except IndexError:
                    break
            return hdr


class BaseImage(object):

    def __init__(self, name):
        self.name = name
        self._data = None
        #self.

    @property
    def data(self):
        if self._data is None:
            return fits.getdata(self.name)



class Mask(BaseMaskHeader):

    """
    Notes:
        -the position angle must be read from the preimage, although this will
         only work if this is a GMOS preimage! the PA has to be somewhere in
         the MDF/ODF

    """

    def __init__(self, file, preimage=None, angle=0):
        """
        For now, the angle must be set manually unless a GMOS preimage
        is available, in which case it is read from it.
        """
        self.file = file
        self.data = fits.getdata(self.file)
        if sys.version_info[0] == 2:
            # by passing self to super, I don't need file in __init__() (?)
            super(BaseMaskHeader, self).__init__()
        else:
            super().__init__(self.file)

    def plot(self, ax=None):
        if ax is None:
            ax = plt
        

