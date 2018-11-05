#!/usr/bin/env python3
# -*- coding: utf-8; -*-
#
# Copyright (C) 2018 Colin B. Macdonald <cbm@m.fsf.org>
#
# This file is part of MLP.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import os, sys, shutil
import hashlib


# if you know the salt string and you know someone's student
# number, you can determine their code.
saltstr = 'salt'

# TODO: should get this from project
basename = 'mt2'
longname = 'Math 253 Midterm 2'


def myhash(s):
    """
    Hash a string to a 5-digit code

    Combine the string with a salt string, compute the md5sum, grab
    the first few digits as an integer between 10000 and 99999.
    """
    hashthis = s + saltstr
    h = hashlib.md5(hashthis.encode('utf-8')).hexdigest()
    return str(int(h[0:8], 16) % 89999 + 10000)


def do_renaming(fromdir, todir):
    print('Searching for foo_<studentnumber>.pdf files in {0}...'.format(fromdir))
    for file in os.scandir(fromdir):
        filename = os.fsdecode(file)
        if filename.endswith(".pdf"):
            sn = filename.partition('_')[2].partition('.')[0]
            assert len(sn) == 8
            code = myhash(sn)
            newname = '{0}_{1}_{2}.pdf'.format(basename, sn, code)
            newname = os.path.join(todir, newname)
            print('  found SN {0}: code {1}, copying "{2}" to "{3}"'.format( \
                sn, code, filename, newname))
            shutil.copyfile(filename, newname)


if __name__ == '__main__':
    from testspecification import TestSpecification

    print('Salt is "{0}"'.format(saltstr))

    spec = TestSpecification()
    spec.readSpec()

    if not os.path.isdir('reassembled'):
        print('"reassembled" directory not found: call the "reassemble" script first?')
        sys.exit()

    try:
        os.mkdir('codedReturn')
    except FileExistsError:
        print('Directory "codedReturn" already exists: if you want to re-run this script, try deleting it first.')
        sys.exit()

    do_renaming('reassembled', 'codedReturn')
    # TODO: return code?


    print('Adding codedReturn/index.html file')
    with open('view_test_template.html', 'r') as htmlfile:
        html = htmlfile.read()
    html = html.replace('__COURSENAME__', longname)
    html = html.replace('__TESTNAME__', basename)

    newname = os.path.join('codedReturn', 'index.html')
    with open(newname, 'w') as htmlfile:
        htmlfile.write(html)


    print('All done: copy "codedReturn/" to your webserver')
