from __future__ import absolute_import, division, print_function

from astropy import units as u
from astropy.io import fits
from astropy.wcs import WCS
import matplotlib
from matplotlib import pyplot as plt
from matplotlib.collections import PatchCollection
from matplotlib.patches import Rectangle
import sys


class BaseHeader(object):

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


class BaseImage(BaseHeader):

    def __init__(self, file):
        self.file = file
        self._data = None
        super().__init__(self.file)

    @property
    def data(self):
        if self._data is None:
            return fits.getdata(self.file)


class Mask(BaseHeader):
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
        self._header = None
        if sys.version_info[0] == 2:
            super(BaseHeader, self).__init__()
        else:
            super().__init__(self.file)
        self._nslits = None
        self._pa = None
        self._pixscale = None

    @property
    def nslits(self):
        """Number of slits"""
        if self._nslits is None:
            return self.header[1]['NAXIS2']

    @property
    def pa(self):
        """Mask position angle"""
        if self._pa is None:
            for h in self.header:
                if 'MASK_PA' in h:
                    return h['MASK_PA']
            return None

    @property
    def pixscale(self):
        """Pixel size in arcsec"""
        if self._pixscale is None:
            return self.header[1]['PIXSCALE'] * u.arcsec

    def slits_collection(self, world=False, ax=None, acq_width=2, **kwargs):
        """Load mask slits as a `matplotlib.patches.PatchCollection`
        object

        If `world=True`, slits will be returned in WCS coordinates. If
        false, they will be returned in image coordinates.

        `ax` should be a `matplotlib.axes.Axes` object. If provided, the
        slits will be plotted in the axis.

        `kwargs` are passed to `PatchCollection`

        If I want to return two collections for the science and
        acquisition slits maybe it's better to return lists of patches
        so the user can make the collections with their own colors and
        styles?

        Returns
        -------
        slits_collection : `matplotlib.patches.PatchCollection`
            patch collection of all science slits.

        ***NOTE: only rectangle slits are implemented so far***
        """
        # slit sizes and positions are given in arcsec
        if world:
            keys = ('RA', 'DEC')
            scale = 1 / 3600
        else:
            keys = ('x_ccd', 'y_ccd')
            scale = 1 / self.pixscale.to(u.arcsec).value
        h = self.header[1]
        science = []
        #acquisition = []
        x = self.data[keys[0]] + scale*self.data['slitpos_x']
        y = self.data[keys[1]] + scale*self.data['slitpos_y']
        for i in range(self.nslits):
            xsize = self.data['slitsize_x'][i]
            ysize = self.data['slitsize_y'][i]
            if self.data['slittype'][i] == 'rectangle':
                if not (xsize == ysize == acq_width):
                    #acquisition.append(
                        #Rectangle((x[i], y[i]), scale*xsize, scale*ysize,
                                  #angle=self.pa+45))
                    science.append(
                        Rectangle((x[i], y[i]), scale*xsize, scale*ysize,
                                  angle=self.pa))
        science_collection = PatchCollection(science, **kwargs)
        #acquisition_collection = PatchCollection(acquisition)
        if isinstance(ax, matplotlib.axes.Axes):
            ax.add_collection(science_collection)
            #ax.add_collection(acquisition_collection)
        return science_collection

    def plot(self, ax=None):
        if ax is None:
            ax = plt
        

