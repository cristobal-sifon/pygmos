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
import six
import sys
import warnings

try:
    import aplpy
    _have_aplpy = True
except ImportError:
    _have_aplpy = False


class BaseMaskHeader(object):

    """Utilities to read general parameters from the mask header

    Parameters
    ----------
    file : str
        name of the mask file
    """

    def __init__(self, file):
        super(BaseMaskHeader, self).__init__()
        self.file = file
        self._header = None
        self._pa = None
        self._pixscale = None

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


class Slit(BaseMaskHeader):

    """A slit in a (GMOS) mask

    Parameters
    ----------
    data : `astropy.table.Row` instance
        slit data as read by running `data = Table(fits.getdata(file))[i]`
        where `file` is the table filename and `i` is an index within
        the table
    file : `str`
        name of the file containing the parent mask
    frame : {'world', 'image', 'ccd'}
        whether to work with the mask in world coordinate system (WCS),
        or image/ccd coordinates (the latter two are equivalent).
        Defaults to "world"

    To do:
        -support for equivalent types of both `data` (e.g., pyfits
         objects, dictionaries) and `file` (e.g., HDU)

    """

    def __init__(self, data, file, frame='world'):
        super(Slit, self).__init__(file)
        self.data = data
        self.file = file
        self.frame = frame
        for name in self.data.colnames:
            setattr(self, name.lower(), self.data[name])
        self.x, self.y = self.get_position()
        self.width, self.height = self.size_in_frame()
        return

    def _assert_slittype(self):
        """Until more slit types are implemented"""
        if self.slittype != 'rectangle':
            msg = 'Only rectangular slits are supported. Skipping' \
                  ' slit of type {0} '.format(self.slittype)
            warnings.warn(msg)
            return False
        return True

    def get_frame(self):
        return self.frame

    def set_frame(self, frame):
        """set coordinate frame to either 'world' or 'image'"""
        assert frame in ('world', 'image', 'ccd'), \
            'Attribute `frame` must be one of "world","image" or "ccd"' \
            ' ("ccd" is an alias for "image").'
        self.frame = frame

    def get_position(self):
        if self.frame == 'world':
            xo = 15 * self.ra
            yo = self.dec
            scale = 1 / 3600
        else:
            xo = self.x_ccd
            yo = self.y_ccd
            scale = 1 / self.pixscale.to(u.arcsec).value
        _pa = (np.pi/180) * self.pa
        dx = scale * (self.slitpos_x*np.cos(_pa) \
                      + self.slitpos_y*np.sin(_pa))
        dy = scale * (self.slitpos_x*np.sin(_pa) \
                      + self.slitpos_y*np.cos(_pa))
        # the signs here simply have to do with the angle convention
        return xo-dx, yo-dy

    def size_in_frame(self, unit='deg'):
        """Slit size in units appropriate to the frame defined for this
        object

        Parameters
        ----------
        unit : `str`
            if `self.frame==world`, then `unit` should be any unit
            accepted by `astropy.coordinates.Angle`

        Returns
        -------
        xsize, ysize : `float`
            slit size in both axes in the requested units
        """
        if self.frame == 'world':
            scale = (1 * u.arcsec).to(unit).value
        else:
            scale = 1 / self.header.pixscale.to(u.arcsec).value
        return scale*self.slitsize_x, scale*self.slitsize_y

    def region(self):
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
        if not self._assert_slittype():
            return
        if self.slittype == 'rectangle':
            region = 'Box({0},{1},{2}",{3}",{4})'.format(
                self.x, self.y, 3600*self.width, 3600*self.height, self.pa)
        return region

    def patch(self, ax=None, **kwargs):
        """Create a `matplotlib.patches` instance

        `kwargs` is passed to the appropriate `matplotlib.patches`
        method (e.g., `Rectangle`)
        """
        if not self._assert_slittype():
            return
        if self.slittype == 'rectangle':
            patch = Rectangle(
                (self.x-self.width/2, self.y-self.height/2),
                self.width, self.height, **kwargs)
        tform = self.rotate()
        patch.set_transform(tform)
        return patch

    def rotate(self):
        """Create a transformation to rotate the slit around its center"""
        return Affine2D().rotate_deg_around(self.x, self.y, self.pa)


class Mask(BaseMaskHeader):
    """GMOS MOS mask object class

    Parameters
    ----------
    file : str
        name of the MOS mask file
    frame : {"world","image","ccd"}
        whether to work with the mask in world coordinate system (WCS),
        or image/ccd coordinates (the latter two are equivalent).
        Defaults to "world"
    """

    def __init__(self, file, frame='world'):
        super(Mask, self).__init__(file)
        self.file = file
        self.data = Table(fits.getdata(self.file))
        self.set_frame(frame)
        self._name = None
        self._nslits = None
        # initialize BaseMaskHeader
        #self._header = None
        # not sure why I need these two?
        #self._pa = None
        #self._pixscale = None

    @property
    def name(self):
        """Mask name"""
        if self._name is None:
            #return super(BaseMaskHeader, self).header[0]['DATALAB']
            return self.header[0]['DATALAB']

    @property
    def nslits(self):
        """Number of slits"""
        if self._nslits is None:
            return self.header[1]['NAXIS2']

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
            slit = Slit(slit, self.file)
            #science.append(self.slit_patch(slit, ax=ax))
            science.append(slit.patch(ax=ax))
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
            #regions.append(self.slit_region(slit))
            slit = Slit(slit, self.file)
            regions.append(slit.region())
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

