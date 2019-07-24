#!/usr/bin/env python3
# -*- coding: utf-8; -*-
#
# Copyright (C) 2019 Colin B. Macdonald <cbm@m.fsf.org>
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

archivename = 'math123_1971S3_{SHORTNAME}'


if __name__ == '__main__':
    # this allows us to import from ../resources
    sys.path.append("..")
    from resources.testspecification import TestSpecification

    spec = TestSpecification()
    spec.readSpec()
    basename = spec.Name
    archivename = archivename.replace('{SHORTNAME}', basename)

    print("""
This script tries to produce a minimal archive of your test:
    "{0}.zip"
This is intended for archival purposes.  Note it would not be easy to
regrade a question within Plom using this archive.  If you ever
anticipate revisiting the grading of this test, you should backup the
entire directory structure.
    """.format(archivename))
    #input('Press Enter to continue...')

    all_ok = True

    print('Creating temporary directory "{0}"'.format(archivename))
    try:
        os.mkdir(archivename)
    except FileExistsError:
        print('Directory "{0}" already exists: if you want to re-run this script, try deleting it first.'.format(archivename))
        sys.exit()


    print('Archiving source pdf files')
    try:
        shutil.copytree(os.path.join('..', 'build', 'sourceVersions'),
                        os.path.join(archivename, 'sourceVersions'), symlinks=False)
    except:
        print('  WARNING: could not archive "build/sourceVersions" directory')
        all_ok = False


    print('Archiving raw scans')
    try:
        shutil.copytree(os.path.join('..', 'scanAndGroup', 'scannedExams'),
                        os.path.join(archivename, 'scannedExams'), symlinks=False)
    except:
        print('  WARNING: could not archive "scanAndGroup/scannedExams" directory')
        all_ok = False
    try:
        os.rmdir(os.path.join(archivename, 'scannedExams', 'png'))
    except:
        print('  WARNING: could not remove supposedly-empty "scanningExams/png" directory')
        all_ok = False


    print('Archiving return pdf files ("codedReturn")')
    # TODO: do we want this or "reassembled"?
    shutil.copytree('codedReturn', os.path.join(archivename, 'codedReturn'), symlinks=False)


    print('Archiving metadata and miscellanea')
    shutil.copy2('testMarks.csv', archivename)
    shutil.copy2(os.path.join('..', 'resources', 'testSpec.json'), archivename)
    # which version was used for each exam number
    shutil.copy2(os.path.join('..', 'resources', 'examsProduced.json'), archivename)
    # the mapping b/w scan file and paper number
    shutil.copy2(os.path.join('..', 'resources', 'examsScanned.json'), archivename)
    # the mapping b/w paper number and student
    shutil.copy2(os.path.join('..', 'resources', 'examsIdentified.json'), archivename)


    # TODO: should we insert a README.txt w/ explanation of these files?


    print('Creating zip file')
    fn = shutil.make_archive(archivename, 'zip', base_dir=archivename)
    print('  created "{0}"'.format(fn))

    print('Removing temp directory')
    shutil.rmtree(archivename)

    print('\nFinished!  The zip file is:\n  {0}'.format(fn))
    print('  (you may want to rename this)')
    if not all_ok:
        print('... but there were some warnings, see above')
