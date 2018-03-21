#!/usr/bin/env python
# shaw@noao.edu  2016-Jun-09

import argparse
import glob, os
import sqlite3
import sys

APERTURES = ['None', '0.5arcsec', '0.75arcsec', '1.0arcsec', '1.5arcsec',
             '2.0arcsec', '5.0arcsec', 'NS0.75arcsec', 'NS1.0arcsec',
             'NS1.5arcsec', 'NS2.0arcsec', 'IFU-2', 'IFU-B', 'IFU-R']
BINFACTORS = ['1 1', '1 2', '1 4', '2 1', '2 2', '2 4', '4 1', '4 2', '4 4']
DISPERSERS = ['MIRROR', 'B600', 'B1200', 'R150', 'R400', 'R831']
FILELIST_TYPES = ['bias', 'dark', 'GCALflat', 'twiflat', 'arc', 'science']
FILTERS = ['open', 'u', 'g', 'r', 'i', 'z', 'Y', 'Z',
           'Lya395', 'HeII', 'HeIIC', 'OIII', 'OIIIC', 'Ha', 'HaC', 'SII', 'CaT']
OBSTYPES = ['ARC', 'BIAS', 'FLAT', 'OBJECT']
OBSCLASS = ['dayCal', 'partnerCal', 'progCal', 'science']
ROI_TYPES = ['Full', 'CentSp', 'CentStamp']

# SQL for various exposure types:
SQL_Arc = '''SELECT file FROM obslog WHERE
    use_me=1 AND ObsType='ARC' AND ObsClass LIKE '%Cal'
    AND Instrument=:Instrument AND RoI=:RoI AND CcdBin=:CcdBin
    AND AperMask=:AperMask AND Disperser LIKE :Disperser AND CentWave=:CentWave
    '''

SQL_ArcP = '''SELECT file FROM obslog WHERE
    use_me=1 AND ObsType='ARC' AND ObsClass='progCal'
    AND Instrument=:Instrument AND RoI=:RoI AND CcdBin=:CcdBin
    AND AperMask=:AperMask AND Disperser LIKE :Disperser AND CentWave=:CentWave
    '''

SQL_Bias = '''SELECT file FROM obslog WHERE
    use_me=1 AND ObsType='BIAS' AND ObsClass LIKE '%Cal'
    AND Instrument=:Instrument AND RoI=:RoI AND CcdBin=:CcdBin
    '''

SQL_Dark = '''SELECT file FROM obslog WHERE
    use_me=1 AND ObsType='DARK' AND ObsClass LIKE '%Cal'
    AND Instrument=:Instrument AND RoI=:RoI AND CcdBin=:CcdBin
    '''

SQL_ImgTwiFlat = '''SELECT file FROM obslog WHERE
    use_me=1 AND ObsClass='dayCal' AND Object='Twilight'
    AND Instrument=:Instrument AND RoI=:RoI AND CcdBin=:CcdBin
    AND Disperser='MIRROR' AND AperMask="None" AND Filter2 LIKE :Filter2
    '''

SQL_SpecTwiFlat = '''SELECT file FROM obslog WHERE
    use_me=1 AND ObsType='OBJECT' AND ObsClass LIKE '%Cal' AND Object='Twilight'
    AND Instrument=:Instrument AND RoI=:RoI AND CcdBin=:CcdBin
    AND AperMask=:AperMask AND Disperser LIKE :Disperser AND CentWave=:CentWave
    '''

SQL_GcalFlat = '''SELECT file FROM obslog WHERE
    use_me=1 AND ObsType='FLAT' AND ObsClass LIKE '%Cal'
    AND Instrument=:Instrument AND RoI=:RoI AND CcdBin=:CcdBin
    AND AperMask=:AperMask AND Disperser LIKE :Disperser AND CentWave=:CentWave
    '''

SQL_Std = '''SELECT file FROM obslog WHERE
    use_me=1 AND ObsType='OBJECT' AND ObsClass LIKE '%Cal'
    AND Instrument=:Instrument AND RoI=:RoI AND CcdBin=:CcdBin
    AND AperMask=:AperMask AND Disperser LIKE :Disperser AND CentWave=:CentWave
    '''

SQL_SciSpec = '''SELECT file FROM obslog WHERE
    use_me=1 AND ObsType='OBJECT' AND ObsClass='science' AND Object LIKE :Object
    AND Instrument=:Instrument AND RoI=:RoI AND CcdBin=:CcdBin
    AND AperMask=:AperMask AND Disperser LIKE :Disperser AND CentWave=:CentWave
    '''

SQL_SciImg = '''SELECT file FROM obslog WHERE
    use_me=1 AND ObsType='OBJECT' AND ObsClass='science' AND Object LIKE :Object
    AND Instrument=:Instrument AND RoI=:RoI AND CcdBin=:CcdBin
    AND Disperser='MIRROR' AND AperMask='None' AND Filter2 LIKE :Filter2
    '''

SQL_Offset = '''SELECT File,DTA_Xoffset FROM obslog WHERE Object LIKE :Object 
    '''

SQL_TYPES = {
             'arc':SQL_Arc,
             'arcP':SQL_ArcP,
             'bias':SQL_Bias,
             'dark':SQL_Dark,
             'gcalFlat':SQL_GcalFlat,
             'sciSpec':SQL_SciSpec,
             'sciImg':SQL_SciImg,
             'std':SQL_Std,
             'twiFlat':SQL_ImgTwiFlat,
             'twiSpecFlat':SQL_SpecTwiFlat,
             'offset':SQL_Offset
             }

def createQuery(listType, queryDict):
    '''Create an SQL statement to select files that match criteria.
        
        Parameters
        ----------
        queryType : str
            Type of exposures to select; one of SQL_TYPES.keys()
        queryDict : dict
            query parameters
        
        Returns
        -------
        SQLstr : str
            SQL query statement to execute
        '''
    # Select a pre-defined SQL statement based on desired type of file list.
    return SQL_TYPES[listType] + dateQuerySegment(queryDict)

def dateQuerySegment(queryDict):
    '''Create an SQL segment to allow any date, or select a range of dates.
        
        Parameters
        ----------
        queryDict : dict
            query parameters
        
        Returns
        -------
        SQLseg : str
            segment of SQL query string
    '''
    dateList = queryDict['DateObs'].split(':')
    if len(dateList) == 1:
        if '*' in dateList[0] or '?' in dateList[0]:
            SQLseg = ' AND DateObs GLOB :DateObs'
        elif 'None' in dateList[0]:
            SQLseg = ''
        else:
            SQLseg = ' AND DateObs=:DateObs'
    else:
        queryDict['date1'],queryDict['date2'] = dateList
        SQLseg = ' AND DateObs>=:date1 AND DateObs <=:date2'
    return SQLseg


def fileListQuery(dbFile, query, selectDict):
    '''From a DB of observation metadata, return a list of files matching the
        specified criteria.
        
        Parameters
        ----------
        dbFile : str
            name of sqlite database created by obslog.py
        query : str
            SQL query statement
        selectDict : dict
            name:value pairs containing all necessary parameters for query
    '''
    with sqlite3.connect(dbFile) as db:
        db.row_factory = sqlite3.Row
        c = db.cursor()
        c.execute(query, selectDict)
        fileList = [row['File'] for row in c.fetchall()]
    return list(f.split(".fits")[0] for f in sorted(fileList))

def offsetQuery(dbFile, query, selectDict):
    '''From a DB of observation metadata, return a list of offsets for matching 
        files.
        
        Parameters
        ----------
        dbFile : str
            name of sqlite database created by obslog.py
        query : str
            SQL query statement
        selectDict : dict
            name:value pairs containing all necessary parameters for query
        '''
    with sqlite3.connect(dbFile) as db:
        db.row_factory = sqlite3.Row
        c = db.cursor()
        c.execute(query, selectDict)
        offsetList = ([row['File'],row['DTA_Xoffset']] for row in c.fetchall())
    return list(offsetList)

def mkOutputFile (outFile, outList):
    '''Write the sorted contents of the list of files to an ASCII file.
        
        Parameters
        ----------
        outFile : str
            Name of output file
        outList : list
            List of selected results
    '''
    with open (outFile, 'w') as o:
        for f in outList:
            line = "%s\n" % (f)
            o.write(line)

def mkFileList(argv):
    '''Create a list of raw image attributes selected from a
       sqlite3 database. 
    '''

    descr_text = 'Construct a list of files or attributes'
    parser = argparse.ArgumentParser(description=descr_text)
    parser.add_argument('dbFile', type=str,
                        help='Name of sqlite3 DB to use')
    parser.add_argument('outFile', type=str,
                        help='Name of output file containing list of input files')
    parser.add_argument('-l', '--listType', choices=SQL_TYPES.keys(),
                        default='Bias', type=str,
                        help='Type of file list')
    parser.add_argument('-a', '--AperMask',
                        default='None', type=str,
                        help='Aperture mask name')
    parser.add_argument('-b', '--CcdBin', choices=BINFACTORS,
                        default='1 1', type=str,
                        help='CCD binning factor (x y)')
    parser.add_argument('-c', '--ObsClass', choices=OBSCLASS,
                        default='BIAS', type=str,
                        help='Class of observation')
    parser.add_argument('-d', '--DateObs',
                        default='*', type=str,
                        help='Calendar date range of exposures' \
                             ' (yyyy-mm-dd:yyyy-mm-dd)')
    parser.add_argument('-e', '--Exposure', type=str,
                        help='File name of exposure')
    parser.add_argument('-f', '--Filter', choices=FILTERS,
                        default='open', type=str,
                        help='Name of filter used')
    parser.add_argument('-g', '--Disperser', choices=DISPERSERS,
                        default='MIRROR', type=str,
                        help='Name of grating, or mirror')
    parser.add_argument('-i', '--Instrument', choices=['GMOS-N', 'GMOS-S'],
                        default='GMOS-N', type=str,
                        help='GMOS instance')
    parser.add_argument('-o', '--Object',
                        default='*', type=str,
                        help='Name of object observed')
    parser.add_argument('-r', '--RoI', choices=ROI_TYPES,
                        default='Full', type=str,
                        help='Type of observation')
    parser.add_argument('-t', '--ObsType', choices=OBSTYPES,
                        default='dayCal', type=str,
                        help='Type of observation')
    parser.add_argument('-w', '--CentWave', type=float,
                        help='Central wavelength')
    args = parser.parse_args()
    
    # A call to fileListQuery will need a dictionary something like the following
    queryDict = {'use_me':1,
        'Instrument':args.Instrument,
        'ObsClass':args.ObsClass,
        'ObsType':args.ObsType,
        'CcdBin':args.CcdBin,
        'RoI':args.RoI,
        'Disperser':args.Disperser,
        'CentWave':args.CentWave,
        'AperMask':args.AperMask,
        'Filter2':args.Filter,
        'Object':'%'+ args.Object + '%',
        'DateObs':args.DateObs
    }
    # Match to substrings in non-default case.
    if args.Filter != 'open':
        queryDict["Filter2"] = args.Filter + '_G%'
    if args.Disperser != 'MIRROR':
        queryDict["Disperser"] = args.Disperser + '+_%'

    # Select a pre-defined SQL statement based on desired type of file list.
    #SQL = SQL_TYPES[args.listType] + dateQuerySegment(queryDict)
    SQL = createQuery(args.listType, queryDict)

    # Expose the query result for testing.
    if args.listType != 'offset':
        fileList = fileListQuery(args.dbFile, SQL, queryDict)
    else:
        fileList = offsetQuery(args.dbFile, SQL, queryDict)
    mkOutputFile(args.outFile, fileList)

if __name__ == '__main__':
    mkFileList(sys.argv)

