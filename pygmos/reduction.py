from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import os
from pyraf import iraf

from . import check_gswave, tasks, utils


def longslit(args, cluster, waves, assoc):
    """
    Reduce longslit data

    """
    combine = []
    mask = 'longslit'
    path = os.path.join(cluster.replace(' ', '_'), mask)
    for wave in waves:
        flat = utils.getFile(assoc, mask=mask, obs='flat', wave=wave)
        # finding the flat is enough to know that the mask exists.
        if flat:
            arc = utils.getFile(assoc, mask=mask, obs='arc', wave=wave)
            science = utils.getFile(assoc, mask=mask, obs='science', wave=wave)
            iraf.chdir(path)
            flat, comb = tasks.Call_gsflat(flat)
            arc = tasks.Call_gsreduce(arc, flat, comb)
            science = tasks.Call_gsreduce(science, flat, comb)
            tasks.Call_gdisplay(science, 1)
            science = tasks.Call_lacos(science, longslit=True)
            tasks.Call_gdisplay(science, 1)
            tasks.Call_gswave(arc)
            tasks.Call_gstransform(arc, arc)

            science = tasks.Call_gstransform(science, arc)
            tasks.Call_gdisplay(science, 1)
            combine.append(tasks.Call_gsskysub(science))
            if len(combine) == len(waves):
                added = tasks.Call_imcombine(cluster, str(mask), combine)
                tasks.Call_gdisplay(added, 1)

        spectra = tasks.Call_gsextract(cluster, mask)
        Naps = raw_input('Number of apertures extracted: ')
        # In case you don't see the message after so many
        # consecutive "Enters"
        while Naps == '':
            Naps = raw_input('Please enter number of apertures extracted: ')
        Naps = int(Naps)
        tasks.Cut_apertures(cluster, Naps)
        delete('tmp*')
        iraf.chdir('../..')
    return


def mos(args, cluster, mask, scienceFiles, assoc, cutdir,
        align_suffix='_aligned'):
    """
    The reduction process for MOS data. It goes through file identification,
    calibration and extraction of spectra.

    """
    Nmasks = 0
    combine = []
    print('Mask {0}'.format(mask), end=2*'\n')
    path = os.path.join(cluster, 'mask{0}'.format(mask))

    for science in scienceFiles.keys():
        flat = utils.getFile(
            assoc, science, mask=int(mask), obs='flat',
            wave=scienceFiles[science])
        # finding the flat is enough to know that the mask exists.
        if not flat:
            print('Not enough data for mask {0} (science file {1})'.format(
                    mask, science))
            continue
        # all observations add up to 1
        Nmasks += 1 / len(scienceFiles.keys())
        arc = utils.getFile(
            assoc, science, mask=int(mask), obs='arc',
            wave=scienceFiles[science])
        utils.Copy_MDF(science, cluster, str(mask))
        iraf.chdir(path)

        flat, comb = tasks.Call_gsflat(flat)
        arc = tasks.Call_gsreduce(arc, flat, comb)
        science = tasks.Call_gsreduce(science, flat, comb)
        tasks.Call_gdisplay(science, 1)
        Nslits = getNslits(science)
        science = tasks.Call_lacos(science, Nslits)
        tasks.Call_gdisplay(science, 1)
        tasks.Call_gswave(arc)
        tasks.Call_gstransform(arc, arc)
        if args.align:
            tasks.Call_align(arc, align, Nslits)
        science = tasks.Call_gstransform(science, arc)
        if args.align:
            tasks.Call_align(science, align_suffix, Nslits)
            tasks.Call_gdisplay(science + align_suffix, 1)
            science = tasks.Call_gsskysub(science, align_suffix)
            tasks.Call_gdisplay(science, 1)
            combine.append(science)
        else:
            tasks.Call_gdisplay(science, 1)
            science = tasks.Call_gsskysub(science, '')
            tasks.Call_gdisplay(science, 1)
            combine.append(science)
        # once we've reduced all individual images
        if len(combine) == len(scienceFiles.keys()):
            added = tasks.Call_imcombine(cluster, str(mask), combine, Nslits)
            tasks.Call_gdisplay(added, 1)
            spectra = tasks.Call_gsextract(cluster, str(mask))
            if args.align:
                aligned = tasks.Call_align(added, align, Nslits)
                tasks.Call_gdisplay(aligned, 1)
        delete('tmp*')
        iraf.chdir('../..')

    # cut spectra
    tasks.Cut_spectra(cluster, str(mask), cutdir=cutdir, spec='2d')
    tasks.Cut_spectra(cluster, str(mask), cutdir=cutdir, spec='1d')
    check_gswave.main(
        cluster, mask, gmos.gswavelength.logfile, 'gswcheck.log')
    return Nmasks


def ns(args, cluster, mask, scienceFiles, assoc, cutdir,
       align_suffix='_aligned'):
    """nod-and-shuffle -- NOT YET IMPLEMENTED"""
    Nmasks = 0
    combine = []
    print('Mask {0}'.format(mask), end=2*'\n')
    path = os.path.join(cluster, 'mask{0}'.format(mask))

    darks = utils.getDarks()
    for science in scienceFiles.keys():
        arc = utils.getFile(
            assoc, science, mask=int(mask), obs='arc',
            wave=scienceFiles[science])
        # finding the arc is enough to know that the mask exists.
        if not arc:
            print('Not enough data for mask {2} (science file {1})'.format(
                    mask, science))
            continue
        # all observations sum to 1
        Nmasks += 1 / len(scienceFiles.keys())
        #arc = getFile(assoc, science, mask = int(mask), obs = 'arc',
                        #wave = scienceFiles[science])
        utils.Copy_MDF(science, cluster, str(mask))
        iraf.chdir(path)

        dark = tasks.Call_gbias(
            darks, fl_over='no', fl_trim='yes', fl_vardq='no', fl_inter='no',
            median='no')
        science = tasks.Call_gprepare(
            science, fl_vardq='no', fl_addmdf='yes')
        science = tasks.Call_gireduce(
            science, bias=dark, fl_over='no', fl_trim='yes', fl_bias='yes',
            fl_dark='no', fl_flat='no', fl_addmdf='no')
        sciwithsky = tasks.Call_gmosaic(
            science, fl_paste='no', geointer='linear', fl_fixpix='no',
            fl_clean='yes')
        science = tasks.Call_gnsskysub(
            science, fl_paste='no', fl_fixpix='no', fl_clean='yes',
            fl_fixnc='no')
        science = tasks.Call_gmosaic(
            science, fl_paste='no', geointer='linear', fl_fixpix='no',
            fl_clean='yes')
        offsetfile = utils.write_offsets(inimages, 'offsets.dat')
        # SHOULD PROBABLY CREATE A BPM, see step 7 of Adam's notes
        # (skipping for now)
        #science = tasks.Call_imcombine(science, 
        
        #flat, comb = tasks.Call_gsflat(flat, fl_over = 'yes',
                                        #fl_inter = 'yes', fl_answer = 'yes')
        #arc = tasks.Call_gsreduce(arc, '', comb)
        #science = tasks.Call_gsreduce(science, '', comb, mode = 'ns1')
        #tasks.Call_gdisplay(science, 1)
        ##Nslits = getNslits(science)
        ##science = tasks.Call_lacos(science, Nslits)
        #science = tasks.Call_gnsskysub(science)
        #tasks.Call_gdisplay(science, 1)
        #tasks.Call_gswave(arc)
        #tasks.Call_gstransform(arc, arc)
        #science = tasks.Call_gsreduce(science, flat, '', mode = 'ns2')
        #science = tasks.Call_gstransform(science, arc)
        ##science = tasks.Call_gsreduce(science, flat, '', bias = False)
        ##if align:
            ##tasks.Call_align(arc, align, Nslits)
        ##science = tasks.Call_gstransform(science, arc)
        ##if align:
            ##tasks.Call_align(science, align_suffix, Nslits)
            ##tasks.Call_gdisplay(science + align_suffix, 1)
            ##science = tasks.Call_gnscombine(science, align_suffix)
        tasks.Call_gdisplay(science, 1)
        delete('tmp*')
        iraf.chdir('../..')

    # cut spectra
    tasks.Cut_spectra(cluster, str(mask), cutdir=cutdir, spec='2d')
    tasks.Cut_spectra(cluster, str(mask), cutdir=cutdir, spec='1d')
    check_gswave.main(
        cluster, mask, gmos.gswavelength.logfile, 'gswcheck.log')
    return Nmasks



