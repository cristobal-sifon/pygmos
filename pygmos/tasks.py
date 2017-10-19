"""
All tasks directly used in the reduction process. Tasks have been defined in
the order that they should be executed.

"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import os
from pyraf import iraf
from iraf import gemini
from iraf import gemtools
from iraf import gmos

from . import utils


def Call_gdisplay(args, image, frame):
    if not args.ds9
        gmos.gdisplay(image, str(frame))
        print('Image', image, 'displayed in frame', frame)
    return


def Call_gsflat(args, flat, fl_over='no', fl_inter='no', fl_answer='no'):
    utils.RemovePreviousFiles(flat, filetype='flat')
    output = '{0}_flat'.format(flat)
    comb = '{0}_comb'.format(flat)
    gmos.gsflat(flat, output, combflat=comb, fl_over=fl_over,
                fl_inter=fl_inter, fl_answer=fl_answer)
    if gmos.gsflat.fl_detec == 'yes':
        os.system('rm %s.fits' %(gmos.gmosaic.outpref + output))
        os.system('rm %s.fits' %(gmos.gmosaic.outpref + comb))
        gmos.gmosaic(output, fl_fixpix='yes', verbose='no',
                    logfile='gmosaic.log')
        gmos.gmosaic(comb, fl_fixpix='yes', verbose='no',
                    logfile='gmosaic.log')
        output = gmos.gmosaic.outpref + output
        comb = gmos.gmosaic.outpref + comb
    return output, comb


def Call_gsreduce(args, img, flat='', grad='', mode='regular'):
    utils.RemovePreviousFiles(img)
    if mode == 'regular':
        if flat:
            gmos.gsreduce(img, gradimage=grad, flatim=flat)
        # will happen when gsreducing the arcs and the first pass
        # of N&S science data
        else:
            gmos.gsreduce(img, fl_flat='no', gradimage=grad)
    elif mode == 'ns1':
        gmos.gsreduce(img, fl_over='no', fl_flat='no', fl_gmosaic='no',
                        fl_gsappwave='no', fl_cut='no', fl_title='no')
    elif mode == 'ns2':
        gmos.gsreduce.outpref = 'r'
        gmos.gsreduce(img, fl_fixpix='no', fl_trim='no', fl_bias='no',
                        fl_flat='no', fl_gsappwave='no', fl_cut='no',
                        fl_title='no', geointer='nearest')
    return gmos.gsreduce.outpref + img


def Call_lacos(args, science, Nslits=0, longslit=False):
    print('-' * 30)
    print('Removing cosmic rays with LACos')
    head = pyfits.getheader(science + '.fits')
    gain = head['GAIN']
    rdnoise = head['RDNOISE']
    outfile = '{0}_lacos.fits'.format(science)

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
        for i in range(1, Nslits + 1):
            j = str(i)
            slit = science + '[sci,' + j + ']'
            outslit = 'slits/' + science + '_' + j
            outmask = 'slits/' + science + '_mask' + j
            iraf.lacos_spec(slit, outslit, outmask, gain=gain, readn=rdnoise)
            iraf.imcopy(outslit, outfile[:-5] + '[SCI,' + j + ',overwrite]',
                        verbose='no')
    utils.delete('lacos*')
    utils.removedir('slits')
    print(outfile[:-5])
    print('-' * 30)
    return outfile[:-5]


def Call_gswave(args, arc):
    print('-' * 30)
    print('Calling gswavelength on', arc)
    gmos.gswavelength(arc)
    print('-' * 30)
    return


def Call_gstransform(args, image, arc):
    print('-' * 30)
    print('Calling gstransform')
    print(image, '-->', end=' ')
    if image[-5:] == 'lacos':
        out = gmos.gstransform.outpref + image[:-6]
    else:
        out = gmos.gstransform.outpref + image
    print(out)
    utils.delete(out + '.fits')
    gmos.gstransform(image, outimage=out, wavtraname=arc)
    print('-' * 30)
    return out


def Call_align(args, inimage, suffix, Nslits):
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


def Call_gsskysub(args, tgsfile, align=''):
    print('-' * 30)
    print('Calling gsskysub')
    print(' ', tgsfile + align, '-->', end=' ')
    out = gmos.gsskysub.outpref + tgsfile + align
    print(out)
    delete(out + '.fits')
    gmos.gsskysub(tgsfile + align, output=out)
    print('-' * 30)
    return out


def Call_gnsskysub(args, inimages):
    print('-' * 30)
    print('Calling gnsskysub')
    print(' ', inimages, '-->', end=' ')
    out = gmos.gnsskysub.outpref + inimages
    print(out)
    utils.delete(out + '.fits')
    gmos.gnsskysub(inimages)
    print('-' * 30)
    return out


def Call_gnscombine(args, cluster, inimages, outimage=''):
    """
    INCOMPLETE
    """
    if not outimage:
        outimage = 'nsc-' + cluster
    print('-' * 30)
    print('Calling gnscombine')
    #write_offsets(inimages)
    print('0 0', file=open('offsets.dat', 'w'))
    print(' ', inimages, '-->', outimage)
    gmos.gnscombine.outimage = outimage
    utils.delete(outimage + '.fits')
    gmos.gnscombine(inimages, 'offsets.dat', outimage,
                    outcheckim=outimage + '_cr', outmedsky=outimage + '_sky')
    print('-' * 30)
    return out


def Call_imcombine(args, cluster, mask, im, Nslits=1):
    print('-' * 30)
    if mask == 'longslit':
        outimage = gmos.gsskysub.outpref + gmos.gstransform.outpref + \
                    gmos.gsreduce.outpref
        outimage += '-' + cluster.replace(' ', '_') + '_ls'
    else:
        outimage = gmos.gsskysub.outpref + gmos.gstransform.outpref + \
                    gmos.gsreduce.outpref
        outimage += '-' + cluster.replace(' ', '_') + '_mask' + mask
    print('Combining images', im, '-->', outimage)
    os.system('cp ' + im[0] + '.fits ' + outimage + '.fits')
    f = pyfits.open(im[0] + '.fits ')
    gain = float(f[0].header['GAINMULT'])
    rdnoise = float(f[0].header['RDNOISE'])
    f.close()
    for i in range(1, Nslits + 1):
        j = str(i)
        inslit = ''
        for jm in im:
            inslit = jm + '[sci,' + j + '],'
        inslit = inslit[:-1] # to remove the last ','
        outslit = outimage + '[sci,' + j + ',overwrite]'
        iraf.imcombine(inslit, output=outslit, gain=gain, rdnoise=rdnoise)
    print('-' * 30)
    return outimage


def Call_gsextract(args, cluster, mask):
    if mask == 'longslit':
        infile = gmos.gsskysub.outpref + gmos.gstransform.outpref + \
                gmos.gsreduce.outpref
        infile += '-' + cluster.replace(' ', '_') + '_ls'
    else:
        infile = gmos.gsskysub.outpref + gmos.gstransform.outpref + \
                gmos.gsreduce.outpref
        infile += '-' + cluster.replace(' ', '_') + '_mask' + mask
    print('-' * 30)
    print('Calling gsextract')
    print(infile, '-->', end=' ')
    out = gmos.gsextract.outprefix + infile
    print(out)
    utils.delete(out + '.fits')
    gmos.gsextract(infile)
    print('-' * 30)
    return out


def Cut_spectra(args, cluster, mask, cutdir='spectra', spec='1d'):
    """
    Takes the extracted spectra and copies them to a single folder called
    spectra/ (by default) in the parent folder. All spectra from all objects 
    will be in the same folder. This is in order for the spectra to be ready
    to cross-correlate with xcsao (for this, you need the RVSAO package for 
    IRAF).
    """
    print('-' * 30)
    print('Cutting spectra...')
    utils.makedir(cutdir, overwrite='no')
    spectra = []
    if spec == '1d':
        prefix = gmos.gsextract.outprefix + gmos.gsskysub.outpref + \
                 gmos.gstransform.outprefix + gmos.gsreduce.outpref
    elif spec == '2d':
        prefix = gmos.gsskysub.outpref + gmos.gstransform.outprefix + \
                 gmos.gsreduce.outpref
    filename = os.path.join(cluster.replace(' ', '_'), 'mask'+mask,
                            prefix+'-'+cluster.replace(' ', '_')+'_mask'+mask)
    Nslits = getNslits(filename)
    for i in range(1, Nslits + 1):
        if i < 10:
            out = cutdir + '/' + cluster.replace(' ', '_') + '_' + \
                mask + '_0' + str(i) + prefix[0]
            utils.delete(out + '.fits')
            iraf.imcopy(filename+'[sci,'+str(i)+']', out, verbose='no')
        else:
            out = cutdir + '/' + cluster.replace(' ', '_') + '_' + \
                mask + '_' + str(i) + prefix[0]
            utils.delete(out + '.fits')
            iraf.imcopy(filename+'[sci,'+str(i)+']', out, verbose='no')
    print('-' * 30)
    return


def Cut_apertures(args, infile, outroot, Naps, path='../../spectra'):
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


