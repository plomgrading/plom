import os
import glob
from collections import defaultdict

os.chdir("extraPages")

for dir in ["originals", "merged", "alreadyProcessed"]:
    if not os.path.exists(dir):
        os.mkdir(dir)

mergeFiles = defaultdict(list)
fullPath = defaultdict(str)

for fname in glob.glob("xt*.png"):
    # File name = xt0000g00v0n0.png
    st = fname[2:6]
    sg = fname[7:9]
    sv = fname[10]
    sn = fname[12]

    print("Copying files for {} = test number {} group {} version {}".format(fname, st, sg, sv))
    gname = "t{}g{}v{}.png".format(st, sg, sv)

    # Copy across the original page-group.
    fullgname = "../readyForMarking/group_{}/version_{}/{}".format(sg, sv, gname)
    fullPath[gname] = fullgname

    os.system("cp {} originals/".format(fullgname))

    # Since one page group may have multiple extra pages we make a list.
    mergeFiles[gname].append(fname)

# Then merge files in that list
for gname in mergeFiles.keys():
    # Merge using imagemagick
    print("Merging into {} the extra pages in {}".format(gname, mergeFiles[gname]))
    cmd = "montage -quiet originals/{}".format(gname)
    # Potentially there should be some user selection of order here.
    for fname in mergeFiles[gname]:
        cmd += " {}".format(fname)
    cmd += " -border 5 -geometry +1+1 merged/{}".format(gname)
    os.system(cmd)

# Then copy the merged files back into place
for gname in mergeFiles.keys():
    print("Copying merged {} back into place".format(gname))
    print("cp merged/{} {}".format(gname, fullPath[gname]))

# Finally move the extra-page images into alreadyProcessed
for gname in mergeFiles.keys():
    for fname in mergeFiles[gname]:
        print("Moving extra page {} to alreadyProcessed directory".format(fname))
        os.system("mv {} alreadyProcessed/".format(fname))

os.chdir("../")
