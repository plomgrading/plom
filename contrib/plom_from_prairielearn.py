#!/bin/env python3

# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2021-2025 Colin B. Macdonald

"""Start a Plom server from a PrairieLearn pdf file upload.

TODO: Needs updating for the legagy->django transition

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
  * Pushing grades back to PrairieLearn: some spreadsheet wrangling TBD.
"""

import csv
import os
from pathlib import Path
import subprocess

# confusingly, there are two: https://gitlab.com/plom/plom/-/issues/1570
import magic
import pandas

import plom
import plom.scan

# TODO: no such thing anymore
# pylint: disable=import-error
# pylint: disable=no-name-in-module
from plom.server import PlomServer  # type: ignore[attr-defined]


########################################################################
# STUFF YOU'LL NEED TO CHANGE
manual_grading_csv = "COURSE_NAME_foo_submissions_for_manual_grading.csv"
# PL's Question ID:
qid = "upload_cat"
# zip_file = 'COURSE_NAME_foo_files_for_manual_grading.zip'
dir_from_zip = "Homework3"
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

# Plom has a "longName" and "shortName"
# TODO: Forest had a function for this
shortname = qid.replace("_", "")

raise NotImplementedError("script needs updating for the legagy->django transition")

# Folder to store the server files
serverdir = Path(f"plom_pl_server-{shortname}")
serverdir.mkdir(exist_ok=True)
# Could wipe the dir before we start
# shutil.rmtree(serverdir)
# serverdir.mkdir(exist_ok=True)

# Prepare the directory ("plom-server init <some_dir>" on command line)
PlomServer.initialise_server(basedir=serverdir)

# Plom's "versions" are more like PL's "alternatives".
# Plom does not yet natively support variants (but that is planned)
# numberOfPages and idPages can be ignored: we're not making these files
spec = plom.SpecVerifier(
    {
        "name": shortname,
        "longName": qid,
        "numberOfVersions": 1,
        "numberOfPages": 2,
        "numberToProduce": -1,
        "numberOfQuestions": 1,
        "idPages": {"pages": [1]},
        "doNotMark": {"pages": []},
        "question": {
            "1": {"pages": [2], "mark": how_many_marks, "select": "fix"},
        },
    }
)
spec.checkCodes()
spec.verifySpec()
spec.saveVerifiedSpec(basedir=serverdir)

cwd = Path.cwd()
try:
    os.chdir(serverdir)
    subprocess.check_call(["plom-server", "users", "--auto", "10"])
    subprocess.check_call(["plom-server", "users", "userListRaw.csv"])
finally:
    os.chdir(cwd)

# Start Plom Server in background, control returns in a few seconds
server = PlomServer(basedir=serverdir)

pwds = {}
with open(serverdir / "userListRaw.csv", "r") as csvfile:
    for row in csv.reader(csvfile):
        pwds[row[0]] = row[1]
os.environ["PLOM_MANAGER_PASSWORD"] = pwds["manager"]
os.environ["PLOM_SCAN_PASSWORD"] = pwds["scanner"]

subprocess.check_call(["plom-create", "class", "fake_classlist.csv"])
try:
    os.chdir(serverdir)
    subprocess.check_call(["plom-create", "make", "--no-pdf"])
finally:
    os.chdir(cwd)

# Any non-PDF files go here, at least its not /dev/null
SEP = Path("someone_elses_problem")
SEP.mkdir(exist_ok=True)

for f in Path(dir_from_zip).glob("*.pdf"):
    uin = f.name.split("_")[1]
    sid = uin_to_sid[uin]
    print(f"Process file {f} with uin={uin}, sid={sid}")
    mime = magic.detect_from_filename(f).mime_type
    if mime != "application/pdf":
        print(f'It appears "{f}" is not a pdf!  its mimetype is "{mime}"')
        f.rename(SEP / f.name)
        continue
    questions = [1]  # Many more options here
    plom.scan.processHWScans(
        f, sid, questions, basedir=serverdir, msgr=("localhost", pwds["scanner"])
    )
    # TODO: do some logging here
    # TODO: be more robust, try catch and move the baddies to SEP

assert server.process_is_running(), "has the server died?"
assert server.ping_server(), "cannot ping server, something gone wrong?"

print("Server seems to still be running: demo setup is complete\n")

print(f"Here are your accounts: (see also {serverdir / 'userListRaw.csv'})")
with open(serverdir / "userListRaw.csv", "r") as csvfile:
    print(csvfile.read())

print('\n*** Now run "plom-client" ***\n')
url = f"{server.server_info['server']}:{server.server_info['port']}"
print(f"  * Server running on {url} with PID {server.pid}\n")
input("Press enter when you want to stop the server...")
server.stop()
print("Server stopped, goodbye!")
