from __future__ import absolute_import, division, print_function

import os
import sys
from time import sleep
from pyraf import iraf
from iraf import gemini, gmos

from . import check_gswave, tasks
from ..inventory import inventory
from ..utilities import utils


def longslit(args, waves, assoc):
    """Reduce longslit data"""
    combine = []
    mask = 'longslit'
    path = os.path.join(args.objectid, mask).replace(' ', '_')

    utils.makedir(path)
        
    for wave in waves:
        flats = inventory.get_file_longslit(assoc, obs='flat', wave=wave)     
        arcs = inventory.get_file_longslit(assoc, obs='arc', wave=wave)
        sciences = inventory.get_file_longslit(assoc, obs='science', wave=wave)

        iraf.chdir(path)
        
        utils.create_symlink(args.bias, args.force_overwrite)

        for flat, arc, science in zip(flats, arcs, sciences):
            #os.symlink(os.path.join('../../', '{}.fits'.format(flat)), '{}.fits'.format(flat))
            #os.symlink(os.path.join('../../', '{}.fits'.format(arc)), '{}.fits'.format(arc))
            #os.symlink(os.path.join('../../', '{}.fits'.format(science)), '{}.fits'.format(science))
            for f in (flat, arc, science):
                utils.create_symlink(f, args.force_overwrite)
            
            flat, comb = tasks.call_gsflat(args, flat)
            arc = tasks.call_gsreduce(args, arc, flat, args.bias, comb)
            science = tasks.call_gsreduce(args, science, flat, args.bias, comb)
            tasks.call_gdisplay(args, science, 1)
            science = tasks.call_lacos(args, science, longslit=True)
            tasks.call_gdisplay(args, science, 1)
            tasks.call_gswave(args, arc)
            tasks.call_gstransform(args, arc, arc)

            science = tasks.call_gstransform(args, science, arc)
            tasks.call_gdisplay(args, science, 1)
            combine.append(tasks.call_gsskysub(args, science))
            
        if len(combine) == len(waves):
            added = tasks.call_imcombine(
                args, str(mask), combine, longslit=True)
            tasks.call_gdisplay(args, added, 1)

        spectra = tasks.call_gsextract(args, added)
        Naps = raw_input('Number of apertures extracted: ')
        # In case you don't see the message after so many
        # consecutive "Enters"
        while Naps == '':
            Naps = raw_input('Please enter number of apertures extracted: ')
        Naps = int(Naps)
        tasks.cut_apertures(args, spectra, '{}_'.format(args.objectid), Naps)
        utils.delete('tmp*')
        iraf.chdir('../..')
    return


def mos(args, mask, files_science, assoc, align_suffix='_aligned'):
    """The reduction process for MOS data.

    It goes through file identification, calibration and extraction of
    spectra.

    """
    Nmasks = 0
    combine = []
    print('Mask {0}'.format(mask), end=2*'\n')
    path = os.path.join(args.objectid, mask).replace(' ', '_')

    # for now
    bias = args.bias

    # debugging - I don't think this should ever happen but hey
    if not files_science:
        raise ValueError('Empty variable `files_science`')

    for science in files_science:
        flat = inventory.get_file(
            assoc, science, mask, obs='flat', wave=files_science[science])
        # finding the flat is enough to know that the mask exists.
        if not flat:
            print('Not enough data for mask {0} (science file {1})'.format(
                    mask, science))
            continue
        # all observations add up to 1
        Nmasks += 1 / len(files_science.keys())
        arc = inventory.get_file(
            assoc, science, mask, obs='arc', wave=files_science[science])
        iraf.chdir(path)

        # first gsreduce the flat to create the gradient image for gscut
        grad = tasks.create_gradimage(args, flat, bias)
        flat, comb = tasks.call_gsflat(args, flat)
        arc = tasks.call_gsreduce(args, arc, flat, bias, grad)
        science = tasks.call_gsreduce(args, science, flat, bias, grad)
        tasks.call_gdisplay(args, science, 1)
        Nslits = utils.get_nslits(science)
        science = tasks.call_lacos(args, science, Nslits)
        tasks.call_gdisplay(args, science, 1)
        tasks.call_gswave(args, arc)
        tasks.call_gstransform(args, arc, arc)
        if args.align:
            tasks.call_align(arc, align, Nslits)
        science = tasks.call_gstransform(args, science, arc)
        if args.align:
            tasks.call_align(science, align_suffix, Nslits)
            tasks.call_gdisplay(args, science + align_suffix, 1)
            science = tasks.call_gsskysub(args, science, align_suffix)
            tasks.call_gdisplay(args, science, 1)
            combine.append(science)
        else:
            tasks.call_gdisplay(args, science, 1)
            science = tasks.call_gsskysub(args, science, '')
            tasks.call_gdisplay(args, science, 1)
            combine.append(science)
        # once we've reduced all individual images
        if len(combine) == len(files_science.keys()):
            added = tasks.call_imcombine(
                args, mask, combine, path, Nslits)
            tasks.call_gdisplay(args, added, 1)
            spectra = tasks.call_gsextract(args, added)
            if args.align:
                aligned = tasks.call_align(added, align, Nslits)
                tasks.call_gdisplay(args, aligned, 1)
        utils.delete('tmp*')
        iraf.chdir('../..')

    # cut spectra
    tasks.cut_spectra(args, added, mask, spec='2d', path=path)
    tasks.cut_spectra(args, spectra, mask, spec='1d', path=path)
    check_gswave.main(
        args.objectid, mask, gmos.gswavelength.logfile, 'gswcheck.log')
    return Nmasks


def ns(args, cluster, mask, files_science, assoc, cutdir,
       align_suffix='_aligned'):
    """nod-and-shuffle -- NOT YET IMPLEMENTED"""
    Nmasks = 0
    combine = []
    print('Mask {0}'.format(mask), end=2*'\n')
    path = os.path.join(args.objectid, 'mask{0}'.format(mask))

    darks = utils.get_darks()
    for science in files_science.keys():
        arc = inventory.get_file(
            assoc, science, mask, obs='arc',
            wave=files_science[science])
        # finding the arc is enough to know that the mask exists.
        if not arc:
            print('Not enough data for mask {2} (science file {1})'.format(
                    mask, science))
            continue
        # all observations sum to 1
        Nmasks += 1 / len(files_science.keys())
        #arc = inventory.get_file(
            #assoc, science, mask, obs='arc', wave=files_science[science])
        #utils.copy_MDF(science, args.objectid, str(mask))
        iraf.chdir(path)

        dark = tasks.call_gbias(
            darks, fl_over='no', fl_trim='yes', fl_vardq='no', fl_inter='no',
            median='no')
        science = tasks.call_gprepare(
            science, fl_vardq='no', fl_addmdf='yes')
        science = tasks.call_gireduce(
            science, bias=dark, fl_over='no', fl_trim='yes', fl_bias='yes',
            fl_dark='no', fl_flat='no', fl_addmdf='no')
        sciwithsky = tasks.call_gmosaic(
            science, fl_paste='no', geointer='linear', fl_fixpix='no',
            fl_clean='yes')
        science = tasks.call_gnsskysub(
            science, fl_paste='no', fl_fixpix='no', fl_clean='yes',
            fl_fixnc='no')
        science = tasks.call_gmosaic(
            science, fl_paste='no', geointer='linear', fl_fixpix='no',
            fl_clean='yes')
        offsetfile = utils.write_offsets(inimages, 'offsets.dat')
        # SHOULD PROBABLY CREATE A BPM, see step 7 of Adam's notes
        # (skipping for now)
        #science = tasks.call_imcombine(science,
        #flat, comb = tasks.call_gsflat(
            #args, flat, fl_over='yes', fl_inter='yes', fl_answer='yes')
        #arc = tasks.call_gsreduce(args, arc, '', comb)
        #science = tasks.call_gsreduce(args, science, '', comb, mode = 'ns1')
        #tasks.call_gdisplay(args, science, 1)
        ##Nslits = utils.get_nslits(science)
        ##science = tasks.call_lacos(args. science, Nslits)
        #science = tasks.call_gnsskysub(science)
        #tasks.call_gdisplay(args, science, 1)
        #tasks.call_gswave(arc)
        #tasks.call_gstransform(arc, arc)
        #science = tasks.call_gsreduce(args, science, flat, '', mode = 'ns2')
        #science = tasks.call_gstransform(science, arc)
        ##science = tasks.call_gsreduce(args, science, flat, '', bias = False)
        ##if align:
            ##tasks.call_align(arc, align, Nslits)
        ##science = tasks.call_gstransform(science, arc)
        ##if align:
            ##tasks.call_align(science, align_suffix, Nslits)
            ##tasks.call_gdisplay(args, science + align_suffix, 1)
            ##science = tasks.call_gnscombine(science, align_suffix)
        tasks.call_gdisplay(args, science, 1)
        utils.delete('tmp*')
        iraf.chdir('../..')

    # cut spectra
    tasks.cut_spectra(args, str(mask), spec='2d')
    tasks.cut_spectra(args, str(mask), spec='1d')
    check_gswave.main(
        args.objectid, mask, gmos.gswavelength.logfile, 'gswcheck.log')
    return Nmasks



