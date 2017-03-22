# -*- coding: utf-8 -*-
import glob
import os
import sys
from pyfits import getheader


def main(program, cluster, bias, masktype='mos', verbose=True):
  if verbose:
    print '#-' * 20 + '#'
    print ' Making inventory for object', cluster
    print '#-' * 20 + '#\n'
  if masktype.lower() == 'mos':
    masks = mos(cluster, program, bias)
  elif masktype.lower() == 'longslit':
    longslit(cluster, program, bias)
  else:
    msg = 'Unknown mask type. Enter "mos" (default) or "longslit".'
    msg += ' Exiting inventory'
    print msg
    exit()
  if verbose:
    print ''
    print '#-' * 20 + '#'
    print ' Inventory ready. Look for "%s.assoc"' %cluster
    print '#-' * 20 + '#'
  if masktype == 'mos':
    return masks
  else:
    return
#------------------------------------------------------------------------------------#
def read(cluster, bias, col=1):
  file = open(cluster + '.assoc')
  # the column number shouldn't change, but just in case.
  masks = []
  while file.readline()[0] == '#':
    pass
  for line in file:
    if line[0] != '#':
      line = line.split()
      m = int(line[col])
      if m not in masks:
        makedir(os.path.join(cluster, 'mask%s' %m))
        masks.append(m)
      os.chdir('%s/mask%s' %(cluster, m))
      os.system('ln -sf ../../%s* .' %bias)
      for i in range(4, 7):
        os.system('ln -sf ../../%s.fits* .' %line[i])
      os.chdir('../..')
  file.close()
  return masks
#------------------------------------------------------------------------------------#
def mos(cluster, program, bias, verbose=True):
  cluster_path = cluster.replace(' ', '_')
  masks = []
  exp = []
  ls = glob.glob('*.fits*')
  for filename in ls:
    head = getheader(filename)
    try:
      if head['MASKNAME'] != 'None':
	if head['OBJECT'].replace(' ', '_') == cluster and \
	    head['OBSCLASS'] == 'science':
	  if (program != '' and program == head['GEMPRGID']) or program == '':
	    obsid = head['OBSID']
	    wave = head['CENTWAVE']
	    exptime = int(head['EXPTIME'])
	    mask = int(head['MASKNAME'][-2:])
	    if [obsid, mask, wave, exptime] not in exp:
              if mask not in masks:
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
        try:
          if float(head['CENTWAVE']) == exp[i][2] and \
              int(head['MASKNAME'][-2:]) == exp[i][1]:
              obsID = exp[i][0]
              wave  = exp[i][2]
              mask  = exp[i][1]
              info.append([filename.replace('.gz', '').replace('.fits', ''), \
                           obsID, mask, head['OBSTYPE'], wave])
        except ValueError:
          pass
    except KeyError:
      pass
  Nfiles = len(info)

  for i in range(Nexp):
    for j in range(3):
      exp[i].append('')

  # only takes one flat and one arc per mask+wavelength for now.
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
  print >>out, 'ObservationID\t\tMask\tWave\t Time\t\tScience\t\tFlat\t\tArc'
  if verbose:
    print 'ObservationID\t\tMask\tWave\t Time\t\tScience\t\tFlat\t\tArc'

  try:
    Ncols = len(exp[0])
  except IndexError:
    raise NameError('Object %s not found' %cluster)
  for i in range(Nexp):
    print >>out, '%s  \t%2d\t%d\t%5d\t\t%s\t%s\t%s' \
                 %(exp[i][0], exp[i][1], int(10 * exp[i][2]),
                   exp[i][3], exp[i][4], exp[i][5], exp[i][6])
    if verbose:
      print '%s  \t%2d\t%d\t%5d\t\t%s\t%s\t%s' \
            %(exp[i][0], exp[i][1], int(10 * exp[i][2]),
              exp[i][3], exp[i][4], exp[i][5], exp[i][6])
    science = exp[i][4] + '.fits'
    flat = exp[i][5] + '.fits'
    arc = exp[i][6] + '.fits'
    os.chdir(cluster_path + '/mask' + str(exp[i][1]))
    os.system('ln -sf ../../' + science + '* .')
    os.system('ln -sf ../../' + flat + '* .')
    os.system('ln -sf ../../' + arc + '* .')
    os.system('ln -sf ../../' + bias + '* .')
    os.chdir('../../')

  # To return all individual masks:
  allmasks = []
  for mask in masks:
    if mask not in allmasks:
      allmasks.append(mask)
  return allmasks

def longslit(cluster, program, bias, verbose=True):
  exp = []
  ls = glob.glob('*.fits')
  for filename in ls:
    head = getheader(filename)
    try:
      if head['OBJECT'].replace(' ', '_') == cluster and \
          head['OBSCLASS'] == 'science':
	if (program != '' and program == head['GEMPRGID']) or program == '':
	  obsid = head['OBSID']
	  wave = head['CENTWAVE']
	  exptime = head['EXPTIME']
	  mask = head['MASKNAME']
	  exp.append([obsid, mask, wave, exptime])
    except KeyError:
      pass
  Nexp = len(exp)

  makedir(os.path.join(cluster, 'longslit'))
  
  info = []
  for filename in ls:
    head = getheader(filename)
    try:
      for i in range(Nexp):
	if head['OBSID'] == exp[i][0] and head['CENTWAVE'] == exp[i][2]:
	  obsID = exp[i][0]
	  info.append([filename[:-5], obsID, exp[i][1],
                   head['OBSTYPE'], exp[i][2]])
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

  out = open(cluster + '.assoc', 'w')
  msg = 'ObservationID\t\tMask\t\tWave\t Time\t\tScience\t\tFlat\t\tArc'
  print >>out, msg
  if verbose:
    print 'ObservationID\t\tMask\t\tWave\t Time\t\tScience\t\tFlat\t\tArc'
  Ncols = len(exp[0])
  for i in range(Nexp):
    print >>out, '%s\t%2d\t%d\t%5d\t\t%s\t%s\t%s' \
                 %(exp[i][0], exp[i][1], int(10*exp[i][2]),
                   exp[i][3], exp[i][4], exp[i][5], exp[i][6])
    if verbose:
      print '%s\t%2d\t%d\t%5d\t\t%s\t%s\t%s' \
            %(exp[i][0], exp[i][1], int(10*exp[i][2]),
              exp[i][3], exp[i][4], exp[i][5], exp[i][6])
    science = exp[i][4] + '.fits'
    flat = exp[i][5] + '.fits'
    arc = exp[i][6] + '.fits'
    try:
      os.chdir(cluster + '/' + str(exp[i][1]))
    except OSError:
      os.chdir(cluster + '/longslit')
    os.system('ln -sf ../../' + science + ' .')
    os.system('ln -sf ../../' + flat + ' .')
    os.system('ln -sf ../../' + arc + ' .')
    os.system('ln -sf ../../' + bias + '.fits* .')
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
  if '=' not in sys.argv[1]:
    cluster = sys.argv[1].replace('?', ' ')
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
