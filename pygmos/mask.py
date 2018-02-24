from __future__ import absolute_import, division, print_function

from astropy import units as u
from astropy.io import fits
from astropy.table import Table
from astropy.wcs import WCS
import matplotlib
from matplotlib import pyplot as plt
from matplotlib.collections import PatchCollection
from matplotlib.patches import Rectangle
from matplotlib.transforms import Affine2D
import numpy as np
import sys
import warnings

try:
    import aplpy
    _have_aplpy = True
except ImportError:
    _have_aplpy = False


class Header(object):

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


class Slit(object):

    def __init__(self):
        return

    def _assert_slittype(self, slit):
        """Until more slit types are implemented"""
        if slit['slittype'] != 'rectangle':
            msg = 'Only rectangular slits are supported. Skipping' \
                  ' slit of type {0} '.format(slit['slittype'])
            warnings.warn(msg)
            return False
        return True

    def slit_region(self, slit):
        """Create a DS9 region in region file format

        Parameters
        ----------
        slit : single-row `dict` or `astropy.table.Table`
            set of parameters defining a single slit

        Returns
        -------
        region : str
            string containing region in region file format
        """
        if not self._assert_slittype(slit):
            return
        x, y = self.slit_position(slit)
        width, height = self.slit_size(slit, unit='arcsec')
        if slit['slittype'] == 'rectangle':
            region = 'Box({0},{1},{2}",{3}",{4})'.format(
                x, y, width, height, self.pa)
        return region

    def slit_patch(self, slit, ax=None, **kwargs):
        """Create a `matplotlib.patches` method

        `kwargs` is passed to the appropriate `matplotlib.patches`
        method (e.g., `Rectangle`)
        """
        if not self._assert_slittype(slit):
            return
        x, y = self.slit_position(slit)
        width, height = self.slit_size(slit)
        if slit['slittype'] == 'rectangle':
            patch = Rectangle(
                (x-width/2, y-height/2), width, height, **kwargs)
        # rotate around the center
        tform = Affine2D().rotate_deg_around(x, y, self.pa)
        patch.set_transform(tform)
        return patch

    def slit_position(self, slit):
        """
        Scale the size of a slit to world or CCD coordinates, if
        necessary
        """
        if self.frame == 'world':
            xo = 15 * slit['RA']
            yo = slit['DEC']
            scale = 1 / 3600
        else:
            xo = slit['x_ccd']
            yo = slit['y_ccd']
            scale = 1 / self.pixscale.to(u.arcsec).value
        _pa = (np.pi/180) * self.pa
        dx = scale * (slit['slitpos_x']*np.cos(_pa) \
                      + slit['slitpos_y']*np.sin(_pa))
        dy = scale * (slit['slitpos_x']*np.sin(_pa) \
                      + slit['slitpos_y']*np.cos(_pa))
        # the signs here simply have to do with the angle convention
        return xo-dx, yo-dy

    def slit_size(self, slit, unit='deg'):
        if self.frame == 'world':
            scale = (1 * u.arcsec).to(unit).value
        else:
            scale = 1 / self.pixscale.to(u.arcsec).value
        return scale*slit['slitsize_x'], scale*slit['slitsize_y']


class Mask(Header, Slit):
    """GMOS MOS mask object class

    Parameters
    ----------
    file : str
        name of the MOS mask file
    frame : {"world","image","ccd"}
        whether to work with the mask in world coordinate system (WCS),
        or image/ccd coordinates (the latter two are equivalent).
        Defaults to "world".

    """

    def __init__(self, file, frame='world'):
        self.file = file
        self.data = Table(fits.getdata(self.file))
        self.set_frame(frame)
        self._name = None
        self._nslits = None
        self._pa = None
        self._pixscale = None
        # initialize BaseHeader and BaseSlit
        self._header = None
        super(Header, self).__init__()
        super(Slit, self).__init__()

    @property
    def name(self):
        """Mask name"""
        if self._name is None:
            return self.header[0]['DATALAB']

    @property
    def nslits(self):
        """Number of slits"""
        if self._nslits is None:
            return self.header[1]['NAXIS2']

    @property
    def pa(self, pa_key='MASK_PA'):
        """Mask position angle"""
        if self._pa is None:
            for h in self.header:
                if pa_key in h:
                    return h[pa_key]
            raise KeyError('Key {0} not found in mask header'.format(pa_key))

    @property
    def pixscale(self):
        """Pixel size in arcsec"""
        if self._pixscale is None:
            return self.header[1]['PIXSCALE'] * u.arcsec

    def get_frame(self):
        return self.frame

    def set_frame(self, frame):
        """set coordinate frame to either 'world' or 'image'"""
        assert frame in ('world', 'image', 'ccd'), \
            'Attribute `frame` must be one of "world","image" or "ccd"' \
            ' ("ccd" is an alias for "image").'
        self.frame = frame

    def slits_collection(self, ax=None, **kwargs):
        """Load mask slits as a `matplotlib.patches.PatchCollection`
        object

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
        science = []
        for slit in self.data:
            if slit['priority'] == '0':
                continue
            science.append(self.slit_patch(slit, ax=ax))
        science_collection = PatchCollection(science, **kwargs)
        if isinstance(ax, matplotlib.axes.Axes):
            ax.add_collection(science_collection)
        return science_collection

    def slits_regions(self, output='default', fig=None, color='green',
                      **kwargs):
        """Create a DS9 region file with the mask slits

        See http://ds9.si.edu/doc/ref/region.html for more information.

        Parameters
        ----------
        slit : single-row `dict` or `astropy.table.Table`
            set of parameters defining a single slit
        output : str
            filename on to which to write the regions. If set to
            'default', then the name will be the name of the mask, with
            a .reg extension (e.g., GS2017BQ076-01.reg), in the working
            directory (not necessarily the directory containing the mask)
        fig : `aplpy.FITSFigure` instance (optional)
            figure on top of which the regions will be plotted
        color : str
            a color supported by ds9 regions (see website)
        kwargs : `aplpy.FITSFigure.show_regions` keyword arguments

        Returns
        -------
        region_file : str
            name of the region file
        """
        regions = []
        for slit in self.data:
            if slit['priority'] == '0':
                continue
            regions.append(self.slit_region(slit))
        if output == 'default':
            output = '{0}.reg'.format(self.name)
        with open(output, 'w') as f:
            if color:
                print('global color={0}'.format(color), file=f)
            if self.frame == 'world':
                print('fk5', file=f)
            for reg in regions:
                print(reg, file=f)
        if _have_aplpy and isinstance(fig, aplpy.FITSFigure):
            fig.show_regions(output, **kwargs)
        return output

