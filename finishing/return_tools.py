# -*- coding: utf-8 -*-

"""Misc tools related to digital return"""

__author__ = "Colin B. Macdonald"
__copyright__ = "Copyright (C) 2018-2019 Colin B. Macdonald"
__license__ = "AGPL-3.0-or-later"
# SPDX-License-Identifier: AGPL-3.0-or-later

import os, sys
import csv
from io import StringIO
import pandas

import utils
from utils import myhash


def import_canvas_csv(canvas_fromfile):
    df = pandas.read_csv(canvas_fromfile, dtype='object')
    print('Loading from Canvas csv file: "{0}"'.format(canvas_fromfile))

    # Note: Canvas idoicy whereby "SIS User ID" is same as "Student Number"
    cols = ['Student', 'ID', 'SIS User ID', 'SIS Login ID', 'Section', 'Student Number']
    assert all([c in df.columns for c in cols]), "CSV file missing columns?  We need:\n  " + str(cols)

    print('Carefully filtering rows w/o "Student Number" including:\n'
          '  almost blank rows, "Points Possible" and "Test Student"s')
    isbad = df.apply(
        lambda x: (pandas.isnull(x['SIS User ID']) and
                   (pandas.isnull(x['Student'])
                    or x['Student'].strip().lower().startswith('points possible')
                    or x['Student'].strip().lower().startswith('test student'))),
        axis=1)
    df = df[isbad == False]

    return df


def find_partial_column_name(df, parthead, atStart=True):
    parthead = parthead.lower()
    if atStart:
        print('Searching for column starting with "{0}":'.format(parthead))
        possible_matches = [s for s in df.columns if s.lower().startswith(parthead)]
    else:
        print('Searching for column containing "{0}":'.format(parthead))
        possible_matches = [s for s in df.columns if s.lower().find(parthead) >= 0]
    print('  We found: ' + str(possible_matches))
    try:
        col, = possible_matches
    except ValueError as e:
        print('  Unfortunately we could not a find a unique column match!')
        raise(e)
    return col


def make_canvas_gradefile(canvas_fromfile, canvas_tofile, test_parthead='Test'):
    print('*** Generating Grade Spreadsheet ***')
    df = import_canvas_csv(canvas_fromfile)

    cols = ['Student', 'ID', 'SIS User ID', 'SIS Login ID', 'Section', 'Student Number']

    testheader = find_partial_column_name(df, test_parthead)
    cols.append(testheader)

    print('Extracting the following columns:\n  ' + str(cols))
    df = df[cols]

    if not all(df[testheader].isnull()):
        print('\n*** WARNING *** Target column "{0}" is not empty!\n'.format(testheader))
        print(df[testheader])
        input('Press Enter to continue and overwrite...')

    print('Loading "testMarks.csv" data')
    # TODO: should we be doing all this whereever testMarks.csv is created?
    marks = pandas.read_csv('testMarks.csv', sep='\t', dtype='object')

    # Make dict: this looks fragile, try merge instead...
    #marks = marks[['StudentID', 'Total']].set_index("StudentID").to_dict()
    #marks = marks['Total']
    #df['Student Number'] = df['Student Number'].map(int)
    #df[testheader] = df['Student Number'].map(marks)

    print('Performing "Left Merge"')
    # TODO: could 'left' lose someone who is in Plom, but missing in Canvas?
    # https://gitlab.math.ubc.ca/andrewr/MLP/issues/159
       
    # MC_edit: i think this works for 159
    dfID = df['Student Number'].tolist()
    marksID = marks['StudentID'].tolist()
    diffList = list(set(marksID).difference(dfID))
    if diffList:
        print('')
        print('***************************************************************************')
        print('found the following students in PLOM who do not appear in the Canvas sheet:')
        print(diffList)
        print('***************************************************************************')
        print('')
    else: 
        print('all PLOM students found in Canvas')
    
    df = pandas.merge(df, marks, how='left',
                      left_on='SIS User ID', right_on='StudentID')
    df[testheader] = df['Total']
    df = df[cols]  # discard again (e.g., PG specific stuff)

    print('Writing grade data "{0}"'.format(canvas_tofile))
    # index=False: don't write integer index for each line
    df.to_csv(canvas_tofile, index=False)
    return df


def canvas_csv_add_return_codes(csvin, csvout):
    print('*** Generating Return Codes Spreadsheet ***')
    df = import_canvas_csv(csvin)

    cols = ['Student', 'ID', 'SIS User ID', 'SIS Login ID', 'Section', 'Student Number']
    assert all([c in df.columns for c in cols]), "CSV file missing columns?  We need:\n  " + str(cols)

    rcode = find_partial_column_name(df, 'Return Code (', atStart=False)
    cols.append(rcode)

    df = df[cols]

    sns = {}
    for i, row in df.iterrows():
        name = row['Student']
        sn = str(row['SIS User ID'])
        sn_ = str(row['Student Number'])
        # as of 2019-10 we don't really dare use Student Number but let's ensure its not insane if it is there...
        if not sn_ == 'nan':
            assert sn == sn_, "Canvas has misleading student numbers: " + str((sn,sn_)) + ", for row = " + str(row)


        assert len(name) > 0, "Student name is empty"
        assert len(sn) == 8, "Student number is not 8 characters: row = " + str(row)

        code = myhash(sn)

        oldcode = row[rcode]
        if pandas.isnull(oldcode):
            oldcode = ''
        else:
            oldcode = str(oldcode)
            # strip commas and trailing decimals added by canvas
            oldcode = oldcode.replace(',', '')
            # TODO: regex to remove all trailing zeros would be less fragile
            oldcode = oldcode.replace('.00', '')
            oldcode = oldcode.replace('.0', '')

        if oldcode == code:
            df.loc[i, rcode] = code  # write back as integer
            sns[sn] = code
            print('  row {0}: already had (correct) code {1} for {2} "{3}"'.format( \
                i, oldcode, sn, name))
        elif oldcode == '':
            df.loc[i, rcode] = code
            sns[sn] = code
            print('  row {0}: adding code {3} for {2} "{1}"'.format( \
                i, name, sn, code))
        else:
            print('  row {0}: oops sn {1} "{2}" already had code {3}'.format( \
                i, sn, name, oldcode))
            print('    (We tried to assign new code {0})'.format(code))
            print('    HAVE YOU CHANGED THE SALT SINCE LAST TEST?')
            raise ValueError('old return code has changed')
    df.to_csv(csvout, index=False)
    print('File for upload to Canvas: "{0}"'.format(csvout))
    return sns


def canvas_csv_check_pdf(sns):
    print('Checking that each codedReturn paper has a corresponding student in the canvas sheet...')
    for file in os.scandir('codedReturn'):
        if file.name.endswith(".pdf"):
            # TODO: this looks rather fragile!
            parts = file.name.partition('_')[2].partition('.')[0]
            sn, meh, code = parts.partition('_')
            if sns.get(sn) == code:
                print('  Good: paper {2} has entry in spreadsheet {0}, {1}'.format(
                    sn, code, file.name))
                sns.pop(sn)
            else:
                print('  ***************************************************************')
                print('  Bad: we found a pdf file that has no student in the spreadsheet')
                print('    Filename: {0}'.format(file.name))
                print('  ***************************************************************')
                #sys.exit()

    # anyone that has a pdf file has been popped from the dict, report the remainders
    if len(sns) == 0:
        print('Everyone listed in the canvas file has a pdf file')
    else:
        print('The following people are in the spreadsheet but do not have a pdf file; did they write?')
        for (sn, code) in sns.items():
            # TODO: name rank and serial number would be good
            print('  SN: {0}, code: {1}'.format(sn, code))


# TODO: maybe pytest makes this?
def raises(expectedException, code=None):
    """Check some lambda expression raises a particular Exception"""
    try:
        code()
    except expectedException:
        return
    raise Failed("DID NOT RAISE")


# TODO: refactor these into proper unit tests
def test_csv():
    print("""
    *** Running tests ***

    Its normal for some verbose output to appear below.  But there should be
    no Exceptions and it should end with "All tests passed".
    """)

    # general test
    s1 = """Student,ID,SIS User ID,SIS Login ID,Student Number,Section,Midterm1,Return Code (241017),Assignments
,,,,,,Muted,,
    Points Possible,,,,,,40,999999999999,(read only)
John Smith,42,12345678,ABCDEFGHIJ01,12345678,101,34,,49
Jane Smith,43,12345679,ABCDEFGHIJ02,12345679,Math 123 S102v,36,,42
Test Student,99,,bbbc6740f0b946af,,,,0
"""
    s2 = """Student,ID,SIS User ID,SIS Login ID,Section,Student Number,Return Code (241017)
John Smith,42,12345678,ABCDEFGHIJ01,101,12345678,349284813368
Jane Smith,43,12345679,ABCDEFGHIJ02,Math 123 S102v,12345679,919005618467
"""
    infile = StringIO(s1)
    outfile = StringIO('')
    sns = canvas_csv_add_return_codes(infile, outfile);
    s = outfile.getvalue()
    assert s == s2 or s.replace('\r\n', '\n') == s2

    # return codes already exist
    infile = StringIO(s2)
    outfile = StringIO('')
    sns = canvas_csv_add_return_codes(infile, outfile);
    s = outfile.getvalue()
    assert s == s2 or s.replace('\r\n', '\n') == s2

    # quotes, commas and decimals
    s1 = """Student,ID,SIS User ID,SIS Login ID,Section,Student Number,Return Code ()
,,,,,,Muted
  Points Possible,,,,,,999999999999
A Smith,42,12345678,ABCDEFGHIJ01,101,12345678,"349,284,813,368.0"
B Smith,43,12348888,ABCDEFGHIJ02,102,12348888,"789,059,192,218.00"
C Smith,44,12347777,ABCDEFGHIJ03,103,12347777,894464449308.0
D Smith,45,12346666,ABCDEFGHIJ04,104,12346666,149766785804.00
"""
    s2 = """Student,ID,SIS User ID,SIS Login ID,Section,Student Number,Return Code ()
A Smith,42,12345678,ABCDEFGHIJ01,101,12345678,349284813368
B Smith,43,12348888,ABCDEFGHIJ02,102,12348888,789059192218
C Smith,44,12347777,ABCDEFGHIJ03,103,12347777,894464449308
D Smith,45,12346666,ABCDEFGHIJ04,104,12346666,149766785804
"""
    infile = StringIO(s1)
    outfile = StringIO('')
    sns = canvas_csv_add_return_codes(infile, outfile);
    s = outfile.getvalue()
    assert s == s2 or s.replace('\r\n', '\n') == s2

    # changing return code is an error
    infile = StringIO("""Student,ID,SIS User ID,SIS Login ID,Section,Student Number,Return Code ()
,,,,,,Muted
Points Possible,,,,,,999999999999
John Smith,42,12345678,ABCDEFGHIJ01,101,12345678,111222333444
""")
    outfile = StringIO('')
    raises(ValueError, lambda: canvas_csv_add_return_codes(infile, outfile))

    # missing "Student" header
    infile = StringIO("""xxStudentxx,SIS User ID,Return Code ()""")
    outfile = StringIO('')
    raises(AssertionError, lambda: canvas_csv_add_return_codes(infile, outfile))

    # missing "SIS User ID" header
    infile = StringIO("""Student,SISTER User IDLE,Return Code ()""")
    outfile = StringIO('')
    raises(AssertionError, lambda: canvas_csv_add_return_codes(infile, outfile))

    # can't find "return code"
    infile = StringIO("""Student,SIS User ID,Retrun C0de ()""")
    outfile = StringIO('')
    raises(AssertionError, lambda: canvas_csv_add_return_codes(infile, outfile))

    # student number too long
    infile = StringIO("""Student,SIS User ID,Return Code ()
,,
,,
John Smith,12345678910,
""")
    outfile = StringIO('')
    raises(AssertionError, lambda: canvas_csv_add_return_codes(infile, outfile))

    # empty student name
    infile = StringIO("""Student,SIS User ID,Return Code ()
,,
,,
John Smith,12345678,
,12348888,
""")
    outfile = StringIO('')
    raises(AssertionError, lambda: canvas_csv_add_return_codes(infile, outfile))

    # missing header rows
    infile = StringIO("""Student,SIS User ID,Return Code ()
John Smith,12345678,
""")
    outfile = StringIO('')
    raises(AssertionError, lambda: canvas_csv_add_return_codes(infile, outfile))

    print("""
    *** All tests passed ***
    """)

    return True
