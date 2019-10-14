#!/usr/bin/env python3
# -*- coding: utf-8; -*-
#
# Copyright (C) 2018-2019 Colin B. Macdonald <cbm@m.fsf.org>
#
# This file is part of Plom.
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

from utils import myhash, SALTSTR as saltstr

# TODO: should get this from project, something like 'Math 253 Midterm 2'
longname = 'Math Exam'  # bland default for now


def do_renaming(fromdir, todir):
    print('Searching for foo_<studentnumber>.pdf files in {0}...'.format(fromdir))
    numfiles = 0
    for file in os.scandir(fromdir):
        if file.name.endswith(".pdf"):
            oldname = file.name.partition('.')[0]
            sn = oldname[-8:]
            assert len(sn) == 8
            assert sn.isdigit()
            code = myhash(sn)
            newname = '{0}_{1}.pdf'.format(oldname, code)
            newname = os.path.join(todir, newname)
            print('  found SN {0}: code {1}, copying "{2}" to "{3}"'.format( \
                sn, code, file.name, newname))
            shutil.copyfile(os.path.join(fromdir, file.name), newname)
            numfiles += 1
    return numfiles


if __name__ == '__main__':
    # this allows us to import from ../resources
    sys.path.append("..")
    from resources.testspecification import TestSpecification

    print('Salt is "{0}"'.format(saltstr))

    spec = TestSpecification()
    spec.readSpec()
    shortname = spec.Name

    # TODO: but "reassembed" is created even if I use 09alt
    reassembles = ['reassembled', 'reassembled_ID_but_not_marked']
    if os.path.isdir(reassembles[0]) and os.path.isdir(reassembles[1]):
        print('You have more than one "reassembled*" directory:')
        print('  decide what you trying to do and run me again.')
        sys.exit()
    elif os.path.isdir(reassembles[0]):
        fromdir = reassembles[0]
    elif os.path.isdir(reassembles[1]):
        fromdir = reassembles[1]
    else:
        print('I cannot find any of the dirs: ' + ', '.join(reassembles))
        print('  Have you called one of the "09" scripts first?')
        sys.exit()
    print('Going to take pdf files from "{0}".'.format(fromdir))

    try:
        os.mkdir('codedReturn')
    except FileExistsError:
        print('Directory "codedReturn" already exists: if you want to re-run this script, try deleting it first.')
        sys.exit()

    numfiles = do_renaming(fromdir, 'codedReturn')
    if numfiles > 0:
        print('renamed and copied {0} files'.format(numfiles))
    else:
        print('no pdf files in "{0}"?  Stopping!'.format(fromdir))
        sys.exit()

    print('Adding codedReturn/index.html file')
    with open('view_test_template.html', 'r') as htmlfile:
        html = htmlfile.read()
    html = html.replace('__COURSENAME__', longname)
    html = html.replace('__TESTNAME__', shortname)

    newname = os.path.join('codedReturn', 'index.html')
    with open(newname, 'w') as htmlfile:
        htmlfile.write(html)


    print('All done!  Next tasks:')
    print('  copy "codedReturn/" to your webserver')
    print('  run 11_write_to_canvas_spreadsheet.py and upload to canvas')
