#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2019 Andrew Rechnitzer and Colin Macdonald"
__credits__ = ["Andrew Rechnitzer", "Colin Macdonald"]
__license__ = "AGPL-3.0-or-later"
# SPDX-License-Identifier: AGPL-3.0-or-later

from glob import glob
import hashlib
import json
import os
import requests
from requests_toolbelt import MultipartEncoder
import shutil
import ssl
import sys
import urllib3
import threading

# ----------------------
sys.path.append("..")
from resources.specParser import SpecParser
from resources.plom_exceptions import *

_userName = "kenneth"

# ----------------------


# If we use unverified ssl certificates we get lots of warnings,
# so put in this to hide them.
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
sslContext = ssl.create_default_context(purpose=ssl.Purpose.CLIENT_AUTH)
sslContext.check_hostname = False
# Server defaults
server = "0.0.0.0"
message_port = 41984
SRmutex = threading.Lock()


# ----------------------


def uploadKnownPage(code, test, page, version, sname, fname, md5sum):
    SRmutex.acquire()
    try:
        param = {
            "user": _userName,
            "fileName": sname,
            "test": test,
            "page": page,
            "version": version,
            "md5sum": md5sum,
        }
        dat = MultipartEncoder(
            fields={
                "param": json.dumps(param),
                "originalImage": (sname, open(fname, "rb"), "image/png"),  # image
            }
        )
        response = session.put(
            "https://{}:{}/admin/knownPages/{}".format(server, message_port, code),
            data=dat,
            headers={"Content-Type": dat.content_type},
            verify=False,
        )
        response.raise_for_status()
    except requests.HTTPError as e:
        if response.status_code == 401:
            raise PlomSeriousException("You are not authenticated.")
        else:
            raise PlomSeriousException("Some other sort of error {}".format(e))
    finally:
        SRmutex.release()

    return response.json()


# ----------------------


def buildDirectories(spec):
    """Build the directories that this script needs"""
    # the list of directories. Might need updating.
    lst = ["sentPages", "discardedPages", "collidingPages"]
    for dir in lst:
        try:
            os.mkdir(dir)
        except FileExistsError:
            pass
    for p in range(1, spec["numberOfPages"] + 1):
        for v in range(1, spec["numberOfVersions"] + 1):
            dir = "sentPages/page_{}/version_{}".format(str(p).zfill(2), v)
            os.makedirs(dir, exist_ok=True)


def extractTPV(name):
    # TODO - replace this with something less cludgy.
    # should be tXXXXpYYvZ.blah
    assert name[0] == "t"
    k = 1
    ts = ""
    while name[k].isnumeric():
        ts += name[k]
        k += 1

    assert name[k] == "p"
    k += 1
    ps = ""
    while name[k].isnumeric():
        ps += name[k]
        k += 1

    assert name[k] == "v"
    k += 1
    vs = ""
    while name[k].isnumeric():
        vs += name[k]
        k += 1
    return (ts, ps, vs)


def doFiling(rmsg, ts, ps, vs, shortName, fname):
    if rmsg[0]:  # msg should be [True, "success", success message]
        # print(rmsg[2])
        shutil.move(
            fname, "sentPages/page_{}/version_{}/{}".format(ps.zfill(2), vs, shortName)
        )
        shutil.move(
            fname + ".qr",
            "sentPages/page_{}/version_{}/{}.qr".format(ps.zfill(2), vs, shortName),
        )
    else:  # msg = [False, reason, message]
        if rmsg[1] == "duplicate":
            print(rmsg[2])
            shutil.move(fname, "discardedPages/{}".format(shortName))
            shutil.move(fname + ".qr", "discardedPages/{}.qr".format(shortName))

        elif rmsg[1] == "collision":
            print(rmsg[2])
            nname = "collidingPages/{}".format(shortName)
            shutil.move(fname, nname)
            shutil.move(fname + ".qr", nname + ".qr".format(shortName))
            # and write the name of the colliding file
            with open(nname + ".collide", "w+") as fh:
                fh.write(rmsg[2])
        # now bad errors
        elif rmsg[1] == "testError":
            print(rmsg[2])
            print("This should not happen - todo = log error in sensible way")
        elif rmsg[1] == "pageError":
            print(rmsg[2])
            print("This should not happen - todo = log error in sensible way")


def sendFiles(fileList):
    for fname in fileList:
        shortName = os.path.split(fname)[1]
        ts, ps, vs = extractTPV(shortName)
        print("Upload {},{},{} = {} to server".format(ts, ps, vs, shortName))
        md5 = hashlib.md5(open(fname, "rb").read()).hexdigest()
        code = "t{}p{}v{}".format(ts.zfill(4), ps.zfill(2), vs)
        rmsg = uploadKnownPage(code, int(ts), int(ps), int(vs), shortName, fname, md5)
        doFiling(rmsg, ts, ps, vs, shortName, fname)


if __name__ == "__main__":
    print(">> This is still a dummy script, but gives you the idea? <<")
    # Look for pages in decodedPages
    spec = SpecParser().spec
    buildDirectories(spec)
    session = requests.Session()
    session.mount("https://", requests.adapters.HTTPAdapter(max_retries=50))

    for p in range(1, spec["numberOfPages"] + 1):
        sp = str(p).zfill(2)
        if not os.path.isdir("decodedPages/page_{}".format(sp)):
            continue
        for v in range(1, spec["numberOfVersions"] + 1):
            print("Looking for page {} version {}".format(sp, v))
            if not os.path.isdir("decodedPages/page_{}/version_{}".format(sp, v)):
                continue
            fileList = glob("decodedPages/page_{}/version_{}/t*.png".format(sp, v))
            sendFiles(fileList)
