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
import ssl
import urllib3
import threading

# ----------------------
from plom_exceptions import *
from specParser import SpecParser

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


def uploadKnownDuplicatePage(code, test, page, version, sname, fname, md5sum):
    print("Still TODO.")
    return
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
            "https://{}:{}/admin/knownDuplicatePages/{}".format(
                server, message_port, code
            ),
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


# def buildDirectories(spec):
#     """Build the directories that this script needs"""
#     # the list of directories. Might need updating.
#     lst = ["sentPages", "sentPages/problemImages"]
#     for dir in lst:
#         try:
#             os.mkdir(dir)
#         except FileExistsError:
#             pass
#     for p in range(1, spec["numberOfPages"] + 1):
#         for v in range(1, spec["numberOfVersions"] + 1):
#             dir = "sentPages/page_{}/version_{}".format(str(p).zfill(2), v)
#             os.makedirs(dir, exist_ok=True)


# def doFiling(rmsg, ts, ps, vs, shortName, fname):
#     if rmsg[0]:  # msg should be [True, "success", success message]
#         print(rmsg[2])
#         print("Todo - mv {} to pages/originalPages/".format(shortName))
#     else:  # msg = [False, reason, message]
#         if rmsg[1] == "duplicate":
#             print(rmsg[2])
#             print("Todo - mv {} to pages/discardedPages/".format(shortName))
#             pass
#         elif rmsg[1] == "collision":
#             print(rmsg[2])
#             print(
#                 "Todo - mv {} to pages/duplicatePages and tell user to review before running 015 = uploadDuplicatePages script (not yet coded)".format(
#                     shortName
#                 )
#             )
#         # now bad errors
#         elif rmsg[1] == "testError":
#             print(rmsg[2])
#             print("This should not happen - todo = log error in sensible way")
#         elif rmsg[1] == "pageError":
#             print(rmsg[2])
#             print("This should not happen - todo = log error in sensible way")


# def sendFiles(fileList):
#     for fname in fileList:
#         shortName = os.path.split(fname)[1]
#         ts, ps, vs = extractTPV(shortName)
#         # print("**********************")
#         print("Upload {},{},{} = {} to server".format(ts, ps, vs, shortName))
#         print(
#             "If successful then move {} to sentPages subdirectory else move to problemImages".format(
#                 shortName
#             )
#         )
#         md5 = hashlib.md5(open(fname, "rb").read()).hexdigest()
#         code = "t{}p{}v{}".format(ts.zfill(4), ps.zfill(2), vs)
#         rmsg = uploadKnownPage(code, int(ts), int(ps), int(vs), shortName, fname, md5)
#         doFiling(rmsg, ts, ps, vs, shortName, fname)


# if __name__ == "__main__":
#     print(">> This is still a dummy script, but gives you the idea? <<")
#     # Look for pages in decodedPages
#     spec = SpecParser().spec
#     buildDirectories(spec)
#     session = requests.Session()
#     session.mount("https://", requests.adapters.HTTPAdapter(max_retries=50))
#
#     for p in range(1, spec["numberOfPages"] + 1):
#         sp = str(p).zfill(2)
#         if not os.path.isdir("decodedPages/page_{}".format(sp)):
#             continue
#         for v in range(1, spec["numberOfVersions"] + 1):
#             print("Looking for page {} version {}".format(sp, v))
#             if not os.path.isdir("decodedPages/page_{}/version_{}".format(sp, v)):
#                 continue
#             fileList = glob("decodedPages/page_{}/version_{}/t*.png".format(sp, v))
#             rmsg = sendFiles(fileList)
