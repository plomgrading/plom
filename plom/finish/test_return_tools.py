# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2019-2021 Colin B. Macdonald
# Copyright (C) 2020 Dryden Wiebe

from io import StringIO
from pytest import raises

from .return_tools import canvas_csv_add_return_codes

"""Tests for canvas_csv_add_return_codes from return_tools"""


def test_csv_general_test():
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
    outfile = StringIO("")
    sns = canvas_csv_add_return_codes(infile, outfile, saltstr="default", digits=12)
    s = outfile.getvalue()
    assert s == s2 or s.replace("\r\n", "\n") == s2

    # return codes already exist
    infile = StringIO(s2)
    outfile = StringIO("")
    sns = canvas_csv_add_return_codes(infile, outfile, saltstr="default", digits=12)
    s = outfile.getvalue()
    assert s == s2 or s.replace("\r\n", "\n") == s2


def test_csv2():
    """Tests quotes, commas and decimals."""
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
    outfile = StringIO("")
    sns = canvas_csv_add_return_codes(infile, outfile, saltstr="default", digits=12)
    s = outfile.getvalue()
    assert s == s2 or s.replace("\r\n", "\n") == s2


def test_csv3():
    """Changing return code is an error."""
    infile = StringIO(
        """Student,ID,SIS User ID,SIS Login ID,Section,Student Number,Return Code ()
,,,,,,Muted
Points Possible,,,,,,999999999999
John Smith,42,12345678,ABCDEFGHIJ01,101,12345678,111222333444
"""
    )
    outfile = StringIO("")
    raises(
        ValueError,
        lambda: canvas_csv_add_return_codes(
            infile, outfile, saltstr="default", digits=12
        ),
    )


def test_csv_missing_header_Student():
    infile = StringIO("""xxStudentxx,SIS User ID,Return Code ()""")
    outfile = StringIO("")
    raises(
        AssertionError,
        lambda: canvas_csv_add_return_codes(infile, outfile, saltstr="default"),
    )


def test_csv_missing_header_SIS_User_ID():
    infile = StringIO("""Student,SISTER User IDLE,Return Code ()""")
    outfile = StringIO("")
    raises(
        AssertionError,
        lambda: canvas_csv_add_return_codes(infile, outfile, saltstr="default"),
    )


def test_csv_cantfind_return_code():
    infile = StringIO("""Student,SIS User ID,R3trun C0de ()""")
    outfile = StringIO("")
    raises(
        AssertionError,
        lambda: canvas_csv_add_return_codes(infile, outfile, saltstr="default"),
    )


def test_csv_studentnum_too_long():
    # UBC specific?
    infile = StringIO(
        """Student,SIS User ID,Return Code ()
,,
,,
John Smith,12345678910,
"""
    )
    outfile = StringIO("")
    raises(
        AssertionError,
        lambda: canvas_csv_add_return_codes(infile, outfile, saltstr="default"),
    )


def test_csv_empty_student_name():
    infile = StringIO(
        """Student,SIS User ID,Return Code ()
,,
,,
John Smith,12345678,
,12348888,
"""
    )
    outfile = StringIO("")
    raises(
        AssertionError,
        lambda: canvas_csv_add_return_codes(infile, outfile, saltstr="default"),
    )


def test_csv_missing_header_rows():
    infile = StringIO(
        """Student,SIS User ID,Return Code ()
John Smith,12345678,
"""
    )
    outfile = StringIO("")
    raises(
        AssertionError,
        lambda: canvas_csv_add_return_codes(infile, outfile, saltstr="default"),
    )
