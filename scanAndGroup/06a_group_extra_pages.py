#!/usr/bin/env python3

__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2018-2020 Andrew Rechnitzer"
__credits__ = ["Andrew Rechnitzer", "Colin Macdonald", "Elvis Cai"]
__license__ = "AGPLv3"

from collections import defaultdict
import glob
import os
import shutil
import shlex
import subprocess

# move into extraPages directory
os.chdir("extraPages")

# create needed directories
for dir in ["originals", "merged", "alreadyProcessed"]:
    if not os.path.exists(dir):
        os.mkdir(dir)

# create list of files for merging and their full paths
mergeFiles = defaultdict(list)
fullPath = defaultdict(str)

# look for every extra page (from manual page identifier)
for fname in glob.glob("xt*.png"):
    # extract strings of test, pagegroup, version numbers
    # plus an additional digit for which extra page this
    # for that particular tgv. ie a student might need
    # two or more extra pages for a question.
    # File name = xt0000g00v0n0.png
    st = fname[2:6]
    sg = fname[7:9]
    sv = fname[10]
    sn = fname[12]

    print(
        "Copying files for {} = test number {} group {} version {}".format(
            fname, st, sg, sv
        )
    )
    # pagegroup file name (not full path)
    gname = "t{}g{}v{}.png".format(st, sg, sv)
    # the full path of the pagegroup image file
    fullgname = "../readyForMarking/group_{}/version_{}/{}".format(sg, sv, gname)
    fullPath[gname] = fullgname
    # Copy across the original page-group.
    shutil.copy(fullgname, "originals")
    # Since one page group may have multiple extra pages we make a list.
    # ie a given group-image will be associated with a list of
    # extra pages [xtblah, xtblah, xtblah,..]
    mergeFiles[gname].append(fname)

# Now merge files in that list into the pagegroup
# using imagemagick montage
for gname in mergeFiles.keys():
    # Merge using imagemagick
    print("Merging into {} the extra pages in {}".format(gname, mergeFiles[gname]))
    cmd = "montage -quiet originals/{}".format(gname)
    # Potentially there should be some user selection of order here.
    # at present this is given by the final digit n in the xtblah name
    for fname in mergeFiles[gname]:
        cmd += " {}".format(fname)
    cmd += " -border 5 -geometry +1+1 merged/{}".format(gname)
    cmd = shlex.split(cmd)
    subprocess.run(cmd, check=True)

# Then copy the merged files back into place
for gname in mergeFiles.keys():
    print("Copying merged {} back into place".format(gname))
    shutil.copy("merged/" + gname, fullPath[gname])

# Finally move the extra-page images into alreadyProcessed
for gname in mergeFiles.keys():
    for fname in mergeFiles[gname]:
        print("Moving extra page {} to alreadyProcessed directory".format(fname))
        shutil.move(fname, "alreadyProcessed")

os.chdir("../")
