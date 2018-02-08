"""
All tasks directly used in the reduction process. Tasks have been defined in
the order that they should be executed.

"""
from __future__ import absolute_import, division, print_function

from astropy.io import fits as pyfits
import os
from time import time

from pyraf import iraf
from iraf import gemini
from iraf import gemtools
from iraf import gmos

from . import utils


def call_gdisplay(args, image, frame):
    if args.ds9:
        gmos.gdisplay(image, str(frame))
        print('Image', image, 'displayed in frame', frame)
    return


def call_gsflat(args, flat, bias='', fl_bias='yes', fl_over='yes',
                fl_inter='no', fl_answer='no'):
    output = '{0}_flat'.format(flat)
    comb = '{0}_comb'.format(flat)
    if utils.skip(args, 'flat'):
        return output, comb
    utils.remove_previous_files(flat, filetype='flat')
    # for now
    bias = args.bias
    if args.nobias:
        fl_bias = ('no' if bias == '' else 'yes')
    gmos.gsflat(flat, output, combflat=comb, bias=bias, fl_bias=fl_bias,
                fl_over=fl_over, fl_inter=fl_inter, fl_answer=fl_answer)
    if gmos.gsflat.fl_detec == 'yes':
        new_output = utils.add_prefix(output, gmos.gmosaic)
        new_comb = utils.add_prefix(comb, gmos.gmosaic)
        os.system('rm {0}.fits'.format(new_output))
        os.system('rm {0}.fits'.format(new_comb))
        gmos.gmosaic(
            output, fl_fixpix='yes', verbose='no', logfile='gmosaic.log')
        gmos.gmosaic(
            comb, fl_fixpix='yes', verbose='no', logfile='gmosaic.log')
        output = new_output
        comb = new_comb
    return output, comb


def call_gsreduce(args, img, flat='', bias='', grad='', mode='regular',
                  fl_bias='yes', fl_over='yes'):
    output = utils.add_prefix(img, gmos.gsreduce)
    if utils.skip(args, 'reduce'):
        return output
    utils.remove_previous_files(img)
    # for now
    bias = args.bias
    if args.nobias:
        fl_bias = ('no' if bias == '' else 'yes')
    if mode == 'regular':
        if flat:
            gmos.gsreduce(
                img, gradimage=grad, flatim=flat, bias=bias, fl_bias=fl_bias,
                fl_over=fl_over)
        # will happen when gsreducing the arcs and the first pass
        # of N&S science data
        else:
            gmos.gsreduce(
                img, fl_flat='no', gradimage=grad, bias=bias, fl_bias=fl_bias,
                fl_over=fl_over)
    elif mode == 'ns1':
        gmos.gsreduce(
            img, bias=bias, fl_over='no', fl_flat='no', fl_bias=fl_bias,
            fl_gmosaic='no', fl_gsappwave='no', fl_cut='no', fl_title='no')
    elif mode == 'ns2':
        gmos.gsreduce.outpref = 'r'
        gmos.gsreduce(img, fl_fixpix='no', fl_trim='no', fl_bias='no',
                      fl_flat='no', fl_gsappwave='no', fl_cut='no',
                      fl_title='no', geointer='nearest')
    return output


def call_lacos(args, science, Nslits=0, longslit=False):
    outfile = '{0}_lacos.fits'.format(science)
    if utils.skip(args, 'lacos'):
        return outfile[:-5]
    print()
    print('-' * 30)
    print()
    print('Removing cosmic rays with LACos ...')
    to = time()
    head = pyfits.getheader(science + '.fits')
    gain = head['GAIN']
    rdnoise = head['RDNOISE']
    utils.delete(outfile)
    os.system('cp  -p ' + science + '.fits ' +  outfile)
    utils.makedir('slits')
    if longslit:
        slit = '{0}[sci,1]'.format(science)
        outslit = os.path.join('slits' '{0}_long'.format(science))
        outmask = os.path.join('slits' '{0}_longmask'.format(science))
        iraf.lacos_spec(slit, outslit, outmask, gain=gain, readn=rdnoise)
        iraf.imcopy(outslit, '{0}[SCI,1,overwrite]'.format(outfile[:-5]),
                    verbose='no')
    else:
        for i in xrange(1, Nslits+1):
            slit = '{0}[sci,{1}]'.format(science, i)
            print('slit =', slit)
            outslit = os.path.join('slits', '{0}_{1}'.format(science, i))
            outmask = os.path.join('slits', '{0}_mask{1}'.format(science, i))
            iraf.lacos_spec(slit, outslit, outmask, gain=gain, readn=rdnoise)
            iraf.imcopy(
                outslit, '{0}[SCI,{1},overwrite]'.format(outfile[:-5], i),
                verbose='no')
    utils.delete('lacos*')
    utils.removedir('slits')
    print(outfile[:-5])
    print('Done in {0:.2f}'.format((time()-to)/60))
    print()
    print('-' * 30)
    print()
    return outfile[:-5]


def call_gswave(args, arc):
    if utils.skip(args, 'wavelength'):
        return
    print('-' * 30)
    print('calling gswavelength on', arc)
    gmos.gswavelength(arc)
    print('-' * 30)
    return


def call_gstransform(args, image, arc):
    if image[-5:] == 'lacos':
        out = gmos.gstransform.outpref + image[:-6]
    else:
        out = gmos.gstransform.outpref + image
    if utils.skip(args, 'transform'):
        return out
    print('-' * 30)
    print('calling gstransform')
    print('{0} -->'.format(image), end=' ')
    print(out)
    utils.delete('{0}.fits'.format(out))
    print('File {0} exists? {1}'.format(image, os.path.isfile(image)))
    gmos.gstransform(image, outimage=out, wavtraname=arc)
    print('-' * 30)
    return out


def call_align(inimage, suffix, Nslits):
    print('-' * 30)
    print('Aligning spectra...')
    outimage = inimage + suffix
    print(inimage, '-->', outimage)
    os.system('cp ' + inimage + '.fits ' + outimage + '.fits')
    utils.delete('shifted*')
    iraf.align(outimage)
    utils.delete('shifted*')
    print('-' * 30)
    return outimage


def call_gsskysub(args, tgsfile, align=''):
    out = gmos.gsskysub.outpref + tgsfile + align
    if utils.skip(args, 'skysub'):
        return out
    print('-' * 30)
    print('calling gsskysub')
    print(' {0}{1} -->'.format(tgsfile, align), end=' ')
    print(out)
    utils.delete('{0}.fits'.format(out))
    print('File {0} exists? {1}'.format(
        tgsfile, os.path.isfile(tgsfile)))
    gmos.gsskysub(tgsfile + align, output=out)
    print('-' * 30)
    return out


def call_gnsskysub(args, inimages):
    out = gmos.gnsskysub.outpref + inimages
    if utils.skip(args, 'skysub'):
        return out
    print('-' * 30)
    print('calling gnsskysub')
    print(' ', inimages, '-->', end=' ')
    print(out)
    utils.delete(out + '.fits')
    gmos.gnsskysub(inimages)
    print('-' * 30)
    return out


def call_gnscombine(args, inimages, outimage=''):
    """
    INCOMPLETE
    """
    if not outimage:
        outimage = 'nsc-' + args.objectid
    if utils.skip(args, 'combine'):
        return outimage
    print('-' * 30)
    print('calling gnscombine')
    #write_offsets(inimages)
    print('0 0', file=open('offsets.dat', 'w'))
    print(' ', inimages, '-->', outimage)
    gmos.gnscombine.outimage = outimage
    utils.delete(outimage + '.fits')
    gmos.gnscombine(
        inimages, 'offsets.dat', outimage,
        outcheckim='{0}_cr'.format(outimage), outmedsky=outimage + '_sky')
    print('-' * 30)
    return outimage


def call_imcombine(args, mask, im, path='./', Nslits=1, longslit=False):
    #if mask == 'longslit':
    if longslit:
        outimage = '{0}{1}{2}-{3}_ls'.format(
            gmos.gsskysub.outpref, gmos.gstransform.outpref,
            gmos.gsreduce.outpref, args.objectid.replace(' ', '_'))
    else:
        outimage = '{0}{1}{2}-{3}_{4}'.format(
            gmos.gsskysub.outpref, gmos.gstransform.outpref,
            gmos.gsreduce.outpref, args.objectid.replace(' ', '_'), mask)
    if utils.skip(args, 'combine'):
        return outimage
    print('-' * 30)
    print('Combining images {0} --> {1}'.format(im, outimage))
    os.system('cp {0}.fits {1}.fits'.format(im[0], outimage))
    f = pyfits.open('{0}.fits'.format(os.path.join(path, im[0])))
    gain = float(f[0].header['GAINMULT'])
    rdnoise = float(f[0].header['RDNOISE'])
    f.close()
    for i in range(1, Nslits+1):
        inslit = ''
        for jm in im:
            inslit = '{0}[sci,{1}],'.format(jm, i)
        # to remove the last ','
        inslit = inslit[:-1]
        outslit = outimage + '[sci,{0},overwrite]'.format(i)
        iraf.imcombine(inslit, output=outslit, gain=gain, rdnoise=rdnoise)
    print('-' * 30)
    return outimage


def call_gsextract(args, mask):
    if mask == 'longslit':
        infile = '{0}{1}{2}-{3}_ls'.format(
            gmos.gsskysub.outpref, gmos.gstransform.outpref,
            gmos.gsreduce.outpref, args.objectid.replace(' ', '_'))
    else:
        infile = '{0}{1}{2}-{3}_mask{4}'.format(
            gmos.gsskysub.outpref, gmos.gstransform.outpref,
            gmos.gsreduce.outpref, args.objectid.replace(' ', '_'), mask)
    out = gmos.gsextract.outprefix + infile
    if utils.skip(args, 'extract'):
        return out
    print('-' * 30)
    print('calling gsextract')
    print(infile, '-->', out)
    utils.delete(out + '.fits')
    gmos.gsextract(infile)
    print('-' * 30)
    return out


def cut_spectra(args, mask, spec='1d'):
    """
    Takes the extracted spectra and copies them to a single folder called
    spectra/ (by default) in the parent folder. All spectra from all objects 
    will be in the same folder. This is in order for the spectra to be ready
    to cross-correlate with xcsao (for this, you need the RVSAO package for 
    IRAF).
    """
    print('-' * 30)
    print('Cutting spectra...')
    utils.makedir(args.cutdir)
    spectra = []
    obj = args.objectid.replace(' ', '_')
    if spec == '1d':
        prefix = gmos.gsextract.outprefix + gmos.gsskysub.outpref + \
                 gmos.gstransform.outprefix + gmos.gsreduce.outpref
    elif spec == '2d':
        prefix = gmos.gsskysub.outpref + gmos.gstransform.outprefix + \
                 gmos.gsreduce.outpref
    filename = os.path.join(
        args.objectid.replace(' ', '_'), 'mask{0}'.format(mask),
        '{0}-{1}_mask{2}'.format(prefix, obj, mask))
    Nslits = utils.get_nslits(filename)
    for i in range(1, Nslits + 1):
        if i < 10:
            #out = cutdir + '/' + cluster.replace(' ', '_') + '_' + \
                #mask + '_0' + str(i) + prefix[0]
            out = os.path.join(
                args.cutdir,
                '{0}_{1}_0{2}{3}'.format(obj, mask, i, prefix[0]))
            #utils.delete(out + '.fits')
            #iraf.imcopy(filename+'[sci,'+str(i)+']', out, verbose='no')
        else:
            #out = cutdir + '/' + cluster.replace(' ', '_') + '_' + \
                #mask + '_' + str(i) + prefix[0]
            out = os.path.join(
                args.cutdir,
                '{0}_{1}_{2}{3}'.format(obj, mask, i, prefix[0]))
            #utils.delete(out + '.fits')
            #iraf.imcopy(filename+'[sci,'+str(i)+']', out, verbose='no')
        utils.delete(out + '.fits')
        iraf.imcopy(filename+'[sci,'+str(i)+']', out, verbose='no')
    print('-' * 30)
    return


def cut_apertures(args, infile, outroot, Naps, path='../../spectra'):
    for i in range(Naps):
        iraf.scopy('{0}[sci,1] {1}{2}'.format(infile, outroot, i),
                   apertures=i)
    return


def MakeBias(args, files=[], date='', logfile='bias.log'):
    """
    The date should be in format "YYYY-MM-DD"

    NOT YET IMPLEMENTED
    """
    for argv in sys.argv:
        if argv[0:9] == 'biasdate=':
            date = argv[9:]
    if argv[0:9] == 'biasfile=':
        return argv[9:]
    if date:
        date2 = date.split('-')
        date2 = date2[0] + date2[1] + date2[2]
    if not files:
        if date:
            ls = glob.glob('*%s*.fits' %date2)
        else:
            ls = glob.glob('*.fits')
        for file in ls:
            head = pyfits.getheader(file)
            try:
                if head['OBJECT'] == 'Bias' and head['OBSTYPE'] == 'BIAS':
                    files.append(file)
            except KeyError:
                pass
    print(date)
    if len(files) == 0:
        print('No bias files from the selected date. Exiting')
        sys.exit()
    output = 'bias'
    biaslist = 'biaslist'
    if date:
        biaslist += '_' + date2
        output   += '_' + date2
    outlist = open(biaslist, 'w')
    for bias in files:
        print(bias, file=outlist)
    gmos.gbias('@' + biaslist, output, logfile=logfile, verbose='no')
    return output


