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


def uploadUnknownPage(sname, fname, md5sum):
    SRmutex.acquire()
    try:
        param = {
            "user": _userName,
            "fileName": sname,
            "md5sum": md5sum,
        }
        dat = MultipartEncoder(
            fields={
                "param": json.dumps(param),
                "originalImage": (sname, open(fname, "rb"), "image/png"),  # image
            }
        )
        response = session.put(
            "https://{}:{}/admin/unknownPages".format(server, message_port),
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
    lst = ["sentPages", "sentPages/unknowns"]
    for dir in lst:
        try:
            os.mkdir(dir)
        except FileExistsError:
            pass


def doFiling(rmsg, shortName, fname):
    if rmsg[0]:  # msg should be [True, "success", success message]
        # print(rmsg[2])
        shutil.move(fname, "sentPages/unknowns/{}".format(shortName))
        shutil.move(
            fname + ".qr", "sentPages/unknowns/{}.qr".format(shortName),
        )
    else:  # msg = [False, reason, message]
        if rmsg[1] == "duplicate":
            print(rmsg[2])
            shutil.move(fname, "discardedPages/{}".format(shortName))
            shutil.move(fname + ".qr", "discardedPages/{}.qr".format(shortName))
        else:
            print(rmsg[2])
            print("This should not happen - todo = log error in sensible way")


def sendUnknownFiles(fileList):
    for fname in fileList:
        md5 = hashlib.md5(open(fname, "rb").read()).hexdigest()
        shortName = os.path.split(fname)[1]
        rmsg = uploadUnknownPage(shortName, fname, md5)
        doFiling(rmsg, shortName, fname)


if __name__ == "__main__":
    # Look for pages in unknowns
    spec = SpecParser().spec
    buildDirectories(spec)
    session = requests.Session()
    session.mount("https://", requests.adapters.HTTPAdapter(max_retries=50))

    fileList = glob("unknownPages/*.png")
    print(fileList)
    sendUnknownFiles(fileList)
