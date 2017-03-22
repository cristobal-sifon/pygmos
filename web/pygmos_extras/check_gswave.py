#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import numpy
import pyfits
import shutil
from pyraf import iraf
from iraf import gemini
from iraf import gmos
from iraf import images
from iraf import tv

def main(cluster, mask, logfile, outfile):
  pathin = os.path.join(cluster, 'mask' + str(mask), logfile)
  outfilename = os.path.join(cluster, 'mask' + str(mask), outfile)
  rms = check(pathin, mask, outfilename)
  over = 0
  wayout = []
  for i in range(len(rms)):
    if rms[i][1] > 0.2:
      over += 1
    if rms[i][1] > 0.25:
      wayout.append(i)
  return wayout # returns the indices of those slits that went wrong.

def check(path, mask, outfilename):
  fits = []
  log = open(path)
  out = open(outfilename, 'w')
  slit = ''
  for line in log:
    if line[:9] == 'NOAO/IRAF': # to restart after every slit
      median = numpy.median(rms)
      std = numpy.std(rms)
      fits.append([slit, median, std])
      slits.append(median)
      sdev.append(std)
      print >>out, slit, median, '%.4f' %std
      slit = ''
    if line[:8] == 'inimages':
      image = line[11:27]
      print >>out, image
      slit = ''
      slits = []
      sdev = []
    if line[:3] == 'MDF':
      slit = int(line[9:])
      rms = []
    if slit:
      if line[:18] == '  ' + image:
	line = line.split()
	rms.append(float(line[4]))
      if line[:16] == image:
	line = line.split()
	rms.append(float(line[6]))
    if line[:17] == 'GSWAVELENGTH exit':
      print 'Mask', mask
      print image
      print numpy.median(slits), min(slits), max(slits)
      print numpy.median(sdev), min(sdev), max(sdev)
      print '-' * 50
      print '-' * 50
  return fits
      
def Look(image, mask):
  gmos.gdisplay(image, '1')
  good = raw_input('Is everything OK with the wavelength calibrations for mask ' + str(mask) + '? [yes]: ')
  if good.lower() == 'no' or good.lower() == 'n':
    return False
  return True

def IdentifyBadSlits(image, Nstars):
  linefile = '../../CuAr_GMOS-ACT.dat'
  N = getNslits(image)
  bad = []
  print 'Introduce the numbers of poorly calibrated slits, separated by comma'
  bad_str = raw_input("(press Enter if you don't know).\t")
  if len(bad_str) > 0:
    bad_str = bad_str.split(',')
    for slit in bad_str:
      bad.append(slit)
  else:
    for i in range(1, N + 1):
      tv.display(image + '[sci,' + str(i) + ']', '1')
      if raw_input('Wavelength calibration for slit ' + str(i) + ' OK? [yes]: ') == 'no':
	bad.append(i)
  print '#' * 15
  print 'Slits with a bad wavelength calibration:'
  for slit in bad:
    x = int(slit) + Nstars
    print slit, '-->',
    if x >= 10:
      print '_0' + str(x)
    else:
      print '_00' + str(x)
  print '#' * 15
  return bad

def ReplaceCalibrations(image, badslits, Nstars, indir = 'database2', outdir = 'database'):
  for slit in badslits:
    x = int(slit) + Nstars
    if x < 10:
      ext = '_00' + str(x)
    else:
      ext = '_0' + str(x)
    infiles = ['id' + image + ext, 'fc' + image + ext]
    for infile in infiles:
      shutil.copyfile(os.path.join(indir, infile), os.path.join(outdir, infile))
    print '*' * 15
    print 'Copied database files for slit', slit
    print '*' * 15
  return

def getNslits(filename):
  f = pyfits.open(filename + '.fits')
  N =  len(f) - 2
  f.close()
  return N

def ManualCheck(lines, pr = False):
  f = open('CuAr_GMOS-ACT.dat')
  skylines = []
  for l in f:
    if l[0] != '#':
      l = l.split()
      skylines.append(float(l[0]))
  
  diff = []
  for line in lines:
    diff.append(100)
    i = len(diff) - 1
    for skyline in skylines:
      if abs(line - skyline) < diff[i]:
	diff[i] = line - skyline

  med = numpy.median(diff)
  std = numpy.std(diff)
  rms = std * numpy.sqrt(len(diff))
  if pr:
    print diff
  print 'med = %.2f;\tstd = %.2f;\trms = %.2f (%d lines)' %(med, std, rms, len(lines))
  return med, std, rms

def getrms(array):
  rms = 0
  avg = numpy.average(array)
  for a in array:
    rms += (a - avg) ** 2
  return numpy.sqrt(rms)

if __name__ == '__main__':
  main()

