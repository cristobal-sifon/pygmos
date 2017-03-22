# -*- coding: utf-8 -*-
import glob
import os
import sys
from pyfits import getheader


def main(program, cluster, masktype = 'mos', verbose = True):
  # if the file exists, just read it
  if os.path.isfile(cluster + '.assoc'):
    masks = read(cluster)
    return masks
  # otherwise, create it
  if verbose:
    print 'Making inventory for object', cluster
  if masktype == 'mos':
    masks = mos(cluster, program)
  elif masktype == 'longslit':
    longslit(cluster)
  else:
    print 'Unknown mask type. Exiting inventory'
    exit()
  if verbose:
    print '#-' * 20 + '#'
    print ' Inventory ready. Look for *.assoc files'
    print '#-' * 20 + '#'
  return masks
#------------------------------------------------------------------------------------#
def read(cluster, col = 1):
  file = open(cluster + '.assoc')
  # the column number shouldn't change, but just in case.
  masks = []
  file.readline()
  for line in file:
    line = line.split()
    m = int(line[col])
    if m not in masks:
      masks.append(m)
  file.close()
  return masks
#------------------------------------------------------------------------------------#
def mos(cluster, program, verbose = True):
  cluster_path = cluster.replace(' ', '_')
  masks = []
  exp = []
  ls = glob.glob('S20*.fits')
  for filename in ls:
    head = getheader(filename)
    try:
      if head['MASKNAME'] != 'None':
	if head['OBJECT'].replace(' ', '_') == cluster and head['OBSCLASS'] == 'science':
	  if (program != '' and program == head['GEMPRGID']) or program == '':
	    obsid = head['OBSID']
	    wave = head['CENTWAVE']
	    exptime = head['EXPTIME']
	    mask = int(head['MASKNAME'][-2:])
	    masks.append(mask)
	    exp.append([obsid, mask, wave, exptime])
    except KeyError:
      pass
  Nexp = len(exp)

  for mask in masks:
    newdir = os.path.join(cluster_path, 'mask' + str(mask))
    makedir(os.path.join(newdir))

  info = []
  for filename in ls:
    head = getheader(filename)
    try:
      for i in range(Nexp):
	if head['OBSID'] == exp[i][0] and head['CENTWAVE'] == exp[i][2]:
	  if int(head['MASKNAME'][-2:]) == exp[i][1]:
	    obsID = exp[i][0]
	    mask = int(head['MASKNAME'][-2:])
	    info.append([filename[:-5], obsID, exp[i][1], head['OBSTYPE'], exp[i][2]])
    except KeyError:
      pass
  Nfiles = len(info)

  for i in range(Nexp):
    for j in range(3):
      exp[i].append('')

  for i in range(Nexp):
    for j in range(Nfiles):
      if exp[i][0] == info[j][1] and exp[i][2] == info[j][4]:
	if info[j][3] == 'OBJECT':
	  exp[i][4] = info[j][0]
	if info[j][3] == 'FLAT':
	  exp[i][5] = info[j][0]
	if info[j][3] == 'ARC':
	  exp[i][6] = info[j][0]

  out = open(cluster_path + '.assoc', 'w')
  print >>out, 'ObservationID\t\tMask\tWave\tTime\t\tScience\t\tFlat\t\tArc'
  if verbose:
    print 'ObservationID\t\tMask\tWave\tTime\t\tScience\t\tFlat\t\tArc'
  Ncols = len(exp[0])
  for i in range(Nexp):
    print >>out, exp[i][0], '\t', exp[i][1], '\t', int(exp[i][2]), '\t',
    print >>out, '%.2f' %exp[i][3], '\t', exp[i][4], '\t', exp[i][5], '\t', exp[i][6]
    if verbose:
      print exp[i][0], '\t', exp[i][1], '\t', int(exp[i][2]), '\t',
      print '%.2f' %exp[i][3], '\t', exp[i][4], '\t', exp[i][5], '\t', exp[i][6]
    science = exp[i][4] + '.fits'
    flat = exp[i][5] + '.fits'
    arc = exp[i][6] + '.fits'
    os.chdir(cluster_path + '/mask' + str(exp[i][1]))
    os.system('ln -s ../../' + science + ' .')# + cluster_path + '/mask' + str(exp[i][1]))
    os.system('ln -s ../../' + flat + ' .')# + cluster_path + '/mask' + str(exp[i][1]))
    os.system('ln -s ../../' + arc + ' .')# + cluster_path + '/mask' + str(exp[i][1]))
    os.chdir('../../')

  # To return all individual masks:
  allmasks = []
  for mask in masks:
    if mask not in allmasks:
      allmasks.append(mask)
  return allmasks

def longslit(cluster, verbose = True):
  exp = []
  ls = glob.glob('*.fits')
  for filename in ls:
    head = getheader(filename)
    try:
      if head['OBJECT'].replace(' ', '_') == cluster and head['OBSCLASS'] == 'science':
	if (program != '' and program == head['GEMPRGID']) or program == '':
	  obsid = head['OBSID']
	  wave = head['CENTWAVE']
	  exptime = head['EXPTIME']
	  mask = head['MASKNAME']
	  exp.append([obsid, mask, wave, exptime])
    except KeyError:
      pass
  Nexp = len(exp)

  makedir(os.path.join(cluster_path, 'longslit'))
  
  info = []
  for filename in ls:
    head = getheader(filename)
    try:
      for i in range(Nexp):
	if head['OBSID'] == exp[i][0] and head['CENTWAVE'] == exp[i][2]:
	  obsID = exp[i][0]
	  info.append([filename[:-5], obsID, exp[i][1], head['OBSTYPE'], exp[i][2]])
    except KeyError:
      pass
  Nfiles = len(info)
  
  for i in range(Nexp):
    for j in range(3):
      exp[i].append('')

  for i in range(Nexp):
    for j in range(Nfiles):
      if exp[i][0] == info[j][1] and exp[i][2] == info[j][4]:
	if info[j][3] == 'OBJECT':
	  exp[i][4] = info[j][0]
	if info[j][3] == 'FLAT':
	  exp[i][5] = info[j][0]
	if info[j][3] == 'ARC':
	  exp[i][6] = info[j][0]

  out = open(cluster_path + '.assoc', 'w')
  print >>out, 'ObservationID\t\tMask\t\tWave\tTime\tScience\t\tFlat\t\tArc'
  if verbose:
    print 'ObservationID\t\tMask\t\tWave\tTime\tScience\t\tFlat\t\tArc'
  Ncols = len(exp[0])
  for i in range(Nexp):
    print >>out, exp[i][0], '\t', exp[i][1], '\t', int(exp[i][2]), '\t',
    print >>out, '%.2f' %exp[i][3], '\t', exp[i][4], '\t', exp[i][5], '\t', exp[i][6]
    if verbose:
      print exp[i][0], '\t', exp[i][1], '\t', int(exp[i][2]), '\t',
      print '%.2f' %exp[i][3], '\t', exp[i][4], '\t', exp[i][5], '\t', exp[i][6]
    science = exp[i][4] + '.fits'
    flat = exp[i][5] + '.fits'
    arc = exp[i][6] + '.fits'
    os.chdir(cluster_path + '/mask' + str(exp[i][1]))
    os.system('ln -s ../../' + science + ' .')# + cluster_path + '/longslit')
    os.system('ln -s ../../' + flat + ' .')# + cluster_path + '/longslit')
    os.system('ln -s ../../' + arc + ' .')# + cluster_path + '/longslit')
    os.chdir('../../')
  return
#------------------------------------------------------------------------------------#
def makedir(name):
  dirs = name.split('/')
  pathback = ''
  for folder in dirs:
    try:
      os.mkdir(folder)
    except OSError:
      pass
    os.chdir(folder)
    pathback += '../'
  os.chdir(pathback)
  return

if __name__ == '__main__':
  program = ''
  cluster = ''
  mask = 'mos'
  verb = True
  for argv in sys.argv:
    if argv[0:7] == 'object=':
      cluster = argv[7:].replace('?', ' ')
    if argv[0:9] == 'program=':
      program = argv[9:]
    if argv == 'mask=longslit' or argv == 'mask=long':
      mask = 'longslit'
    if argv[0:8] == 'verbose=':
      if argv[8:9] == 'F' or argv[8:9].lower() == 'n':
	verb = False
  main(program, cluster, masktype = mask, verbose = verb)