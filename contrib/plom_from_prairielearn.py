#!/bin/env python3

# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2021 Colin B. Macdonald

"""Start a Plom server from a PrairieLearn pdf file upload.

Instructions:
  * Make a directory containing:
      - this python script
      - foo_submissions_for_manual_grading.csv
      - foo_files_for_manual_grading.zip
  * Latter two files come from PrairieLearn -> Assessments -> Homework3 -> Downloads
      - unzip the zip file
  * Get Plom, or use a container:
      - `docker pull plomgrading/server`
      - `docker run -it --rm -p 41984:41984 -v $PWD:/exam:z plomgrading/server bash
      - You're inside the container: run this script.
      - TODO: probably you can do `python3 <script>` instead of `bash`.
      - `plom-server` will still be running.
  * Any files that cannot be processed are in `someone_elses_problem`.
      - (in theory anyway, its still a bit fragile).
  * Use Plom-Client and connect to `localhost:41984`.
"""

import csv
import os
from pathlib import Path
import subprocess
import shutil
import time

import pandas
import plom
# confusingly, there are two: https://gitlab.com/plom/plom/-/issues/1570
import magic


########################################################################
# STUFF YOU'LL NEED TO CHANGE
manual_grading_csv = 'COURSE_NAME_foo_submissions_for_manual_grading.csv'
qid = 'upload_cat'
# zip_file = 'COURSE_NAME_foo_files_for_manual_grading.zip'
dir_from_zip = 'Homework3'
# Plom does only integer grades
how_many_marks = 5
########################################################################


df = pandas.read_csv(manual_grading_csv, dtype="object")

# Only some rows in the sheet match this QuestionID (qid).
# Note: Plom only supports 8-digit UBC-style student numbers so we
# make some fake ones and `uin_to_sid`, a mapping from uin to them.
uin_to_sid = {}
with open("fake_classlist.csv", "w") as csvfile:
    n = 20000000
    f = csv.writer(csvfile)
    f.writerow(["id", "studentName"])
    for r in df.itertuples():
        if r.qid == qid:
            n += 1
            uin_to_sid[r.uin] = n
            f.writerow([n, r.uin])

# terrible, don't do this, fix PlomDemo object instead!
# subprocess.run(['killall', 'plom-server'])

# TODO: just erase everything for now
subprocess.check_call(['rm', '-rf', 'userListRaw.csv', 'markedQuestions', 'pages', 'pleaseCheck', 'serverConfiguration', 'specAndDatabase', 'userRubricPaneData', 'submittedHWByQ'])

# TODO: Forest had a function for this
shortname = qid.replace('_', '')

# TODO: Plom's versions are more like PL's alternatives
# Plom does not yet natively support variants (but that is planned)
# numberOfPages and idPages can be ignored: we're not making these files
spec = plom.SpecVerifier({
    'name': shortname,
    'longName': qid,
    'numberOfVersions': 1,
    'numberOfPages': 2,
    'numberToProduce': -1,
    'numberToName': -1,
    'numberOfQuestions': 1,
    'idPages': {'pages': [1]},
    'doNotMark': {'pages': []},
    'question': {
        '1': {'pages': [2], 'mark': how_many_marks, 'select': 'fix'},
    }
})
spec.checkCodes()
spec.verifySpec()

subprocess.check_call(['plom-server', 'init'])
spec.saveVerifiedSpec()
subprocess.check_call(['plom-server', 'users', '--auto', '10'])
subprocess.check_call(['plom-server', 'users', 'userListRaw.csv'])

# TODO: use new demo object
print('*'*80)
serverproc = subprocess.Popen(['plom-server', 'launch'])
time.sleep(0.1)
try:
    serverproc.wait(2.0)
except subprocess.TimeoutExpired:
    pass
else:
    r = serverproc.returncode
    print("Server has prematurely stopped with return code {}".format(r))
    raise RuntimeError("Server didn't start.  Is one already running?  See errors above.")

pwds = {}
with open("userListRaw.csv", "r") as csvfile:
    for row in csv.reader(csvfile):
        pwds[row[0]] = row[1]
os.environ["PLOM_MANAGER_PASSWORD"] = pwds["manager"]
os.environ["PLOM_SCAN_PASSWORD"] = pwds["scanner"]

subprocess.check_call(['plom-build', 'class', 'fake_classlist.csv'])
subprocess.check_call(['plom-build', 'make', '--no-pdf'])

sub = Path('submittedHWByQ')
sub.mkdir(exist_ok=True)

SEP = Path('someone_elses_problem')
SEP.mkdir(exist_ok=True)

for f in Path(dir_from_zip).glob('*.pdf'):
    uin = f.name.split('_')[1]
    sid = uin_to_sid[uin]
    print(f, uin, sid)
    # plom is VERY particular about the filenames
    newfile = sub / f"{uin}.{sid}.1.pdf"
    shutil.copyfile(f, newfile)
    mime = magic.detect_from_filename(f).mime_type
    if mime != "application/pdf":
        print('It appears "{}" is not a pdf!  its mimetype is "{}"'.format(f, mime))
        shutil.copyfile(f, SEP / f.name)
        continue
    # TODO: do some logging here
    subprocess.check_call(['plom-hwscan', 'process', '-q', '1', newfile, f"{sid}"])
    # TODO: be more robust, try catch and move the baddies to SEP

print("\n\nHere are your accounts in plain-text! :-X")
subprocess.check_call(['cat', 'userListRaw.csv'])
