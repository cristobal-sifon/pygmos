#!/usr/bin/env python
# shaw@noao.edu  2016-May-24
from __future__ import print_function

import argparse
import glob, os
import sqlite3
import sys

from astropy.io import fits

# Mapping of data header keywords to DB field names and DB types
KW_MAP = [('FILE', 'File', 'TEXT UNIQUE ON CONFLICT IGNORE'),
          ('DATE-OBS', 'DateObs', 'TEXT NOT NULL'),
          ('TIME-OBS', 'TimeObs', 'TEXT NOT NULL'),
          ('INSTRUME', 'Instrument', 'TEXT'),
          ('OBJECT',   'Object', 'TEXT'),
          ('RA',       'RA', 'REAL'),
          ('DEC',      'Dec', 'REAL'),
          ('OBSTYPE',  'ObsType', 'TEXT NOT NULL'),
          ('OBSCLASS', 'ObsClass', 'TEXT'),
          ('CCDSUM',   'CcdBin', 'TEXT NOT NULL'),
          ('DETRO1YS', 'RoI', 'TEXT NOT NULL'),
          ('NODMODE',  'NodMode', 'TEXT DEFAULT "NONE"'),
          ('NODPIX',   'NS_Shift', 'INTEGER DEFAULT 0'),
          ('NODCOUNT', 'NS_Cycles', 'INTEGER DEFAULT 0'),
          ('DTAX',     'DTA_Xoffset', 'REAL DEFAULT 0.'),
          ('FILTER1',  'Filter1', 'TEXT NOT NULL'),
          ('FILTER2',  'Filter2', 'TEXT NOT NULL'),
          ('GRATING',  'Disperser', 'TEXT NOT NULL'),
          ('MASKNAME', 'AperMask', 'TEXT NOT NULL'),
          ('MASKTYP',  'MaskType', 'TEXT NOT NULL'),
          ('PA',       'Rotator', 'REAL NOT NULL'),
          ('GRWLEN',   'CentWave', 'REAL NOT NULL'),
          ('EXPTIME',  'T_exp', 'REAL NOT NULL'),
          ('AIRMASS',  'Airmass', 'REAL')]

OBS_FIELDS = [('NULL', 'obs_id', 'INTEGER PRIMARY KEY'),
              ('NULL', 'use_me', 'INTEGER DEFAULT 1'),
              ('NULL', 'N_ext',  'INTEGER DEFAULT 0')]

MC_FIELDS = [('cal_id',   'INTEGER PRIMARY KEY'),
            ('File',      'TEXT UNIQUE ON CONFLICT IGNORE'),
            ('CalDate',   'TEXT NOT NULL'),
            ('ProcType',  'TEXT NOT NULL DEFAULT "MasterCal"'),
            ('ObsType',   'TEXT NOT NULL'),
            ('ObsMode',   'TEXT NOT NULL'),
            ('RoI',       'TEXT NOT NULL'),
            ('CcdBin',    'TEXT NOT NULL'),
            ('Filter',    'TEXT'),
            ('Disperser', 'TEXT'),
            ('Slit',      'TEXT')]

ROIMAP = {'4608': 'FullFrame', '1024': 'CentSpectrum', '300': 'CentStamp'}
MASKMAP = {'-1': 'IFU', '0': 'None', '1': 'Mask'}


def kwToFloat(obsDict, kw, fmt):
    '''Convert keyword value from str to float.
        Parameters
        ----------
        obsDict : dictionary
            dictionary of selected observation metadata from header
        kw : str
            Name of keyword
        fmt : str
            format for conversion to float
    '''
    try:
        val = float(obsDict[kw])
    except ValueError:
        pass
    else:
        obsDict[kw] = fmt % (val)

def setRoiType(obsDict):
    '''The CCD read-out Region of Interest is given by pixel value/extent
        rather than a mnumonic, so we use the values found in GOA searches.
        Parameters
        ----------
        obsDict : dictionary
           dictionary of selected observation metadata from header
    '''
    size = int(obsDict['RoI']) * int(obsDict['CcdBin'].split()[1])
    if size == 1024:
        obsDict['RoI'] = 'CentSp'
    elif size > 1024:
        obsDict['RoI'] = 'Full'
    else:
        obsDict['RoI'] = 'Unknown'

def addObsClass(obsDict):
    '''Early epoch GMOS data lack an OBSCLASS keyword, so infer one.
        '''
    obsType = obsDict['ObsType']
    if obsType in ['BIAS','DARK','ARC','FLAT']:
        return 'Cal'
    elif obsType == 'OBJECT':
        return 'science'

def obsLog(args):
    """Construct an observation log from header keywords in FITS files.
    """

    descr_text = 'Construct an observation log from a directory of data files'
    parser = argparse.ArgumentParser(description=descr_text)
    parser.add_argument('dbFile', type=str,
                        help='Name of sqlite3 file to create')
    parser.add_argument('-f', '--focus', action="store_true",
                        help='Include focus exposures in log')
    parser.add_argument('-v', '--verbose', action="store_true",
                        help='Print log to STDOUT')
    args = parser.parse_args()

    fields = list(zip(*KW_MAP)[1])
    kwds = list(zip(*KW_MAP)[0])
    if args.verbose:
        print(', '.join(i for i in fields))
    lines = []
    fileList = glob.glob('./*.fits') + glob.glob('./*.fz')
    for file in fileList:
        with (fits.open(file)) as hduList:
            #hduList.verify(option='silentfix')
            hd0 = hduList[0].header
            if len(hduList) > 1:
                hd1 = hduList[1].header
            else:
                hd1 = hd0
            values = []
            for kw in kwds:
                # protect against missing keywords in header
                try:
                    values.append(hd0[kw])
                except KeyError:
                    if kw == 'CCDSUM':
                        values.append(hd1[kw])
                    else:
                        values.append(' ')
            obsDict = dict(zip(fields, values))

            # Set proper data formatting and filename
            obsDict['use_me'] = 1
            obsDict['N_ext'] = len(hduList) - 1
            obsDict['File'] = file.replace('./','')
            #obsDict['DateObs'] += 'T' + obsDict['TimeObs']
            if obsDict['ObsClass'] == ' ':
                obsDict['ObsClass'] = addObsClass(obsDict)
            kwToFloat(obsDict, 'T_exp', '%.2f')
            kwToFloat(obsDict, 'RA', '%.8f')
            kwToFloat(obsDict, 'Dec', '%.8f')
            #kwToFloat(obsDict, 'DTA_Xoffset', '%.4f')
            obsDict['DTA_Xoffset'] = \
                '%.3f' % (float(obsDict['DTA_Xoffset']) / 13.5)
            kwToFloat(obsDict, 'Rotator', '%.1f')
            kwToFloat(obsDict, 'Airmass', '%.2f')
            setRoiType(obsDict)
            obsDict['MaskType'] = MASKMAP[str(obsDict['MaskType'])]

            if obsDict['ObsType'] != 'focus' or args.focus:
                lines.append(obsDict)
                if args.verbose:
                    print(', '.join(str(obsDict[x]) for x in fields))

    # Create DB table
    fieldNames = OBS_FIELDS + KW_MAP
    with sqlite3.connect(args.dbFile) as db:
        mkDbTable(db, 'obslog', list(zip(*fieldNames)[1]),
                  list(zip(*fieldNames)[2]))

        # Populate the table of observations
        for obs in lines:
            dbAddEntry(db, 'obslog', obs)

#mkDbTable(db, 'masterCal', list(zip(*MC_FIELDS)[0]), list(zip(*MC_FIELDS)[1]))

def mkDbTable(db, tableName, fields, storage):
    """ Create or update tables in an sqlite3 database.
        Parameters
        ----------
        db : address
            descriptor for sqlite3 database file
        tableName : str
            name of DB table to be created
        fields : list of str
            field names for DB table
        storage : list of str
            strorage info for fields
    """

    cursor = db.cursor()
    # Turn on foreign key support for this DB
    #cursor.execute('''PRAGMA foreign_keys = 1''')

    # Table of observations
    entries = ', '.join(' '.join(zip(fields, storage)[i]) for i in 
range(len(fields)))
    sql = '''CREATE TABLE IF NOT EXISTS %s(%s)
        ''' % (tableName, entries)
    cursor.execute(sql)

    db.commit()

def dbAddEntry(db, tableName, fieldDict):
    """Enter observation into an sqlite3 database.
        Parameters
        ----------
        db : address
            descriptor for sqlite3 database file
        tableName : str
            name of DB table to be updated
        fieldDict: dictionary
            all required fields+values
    """
    
    fields = ', '.join(fieldDict.keys())
    values = ':' + ',:'.join(fieldDict.keys())
    sql = "INSERT INTO %s(%s) VALUES(%s)" % (tableName, fields, values)
    
    cursor = db.cursor()
    cursor.execute(sql, fieldDict)

    db.commit()

if __name__ == '__main__':
    obsLog(sys.argv)

