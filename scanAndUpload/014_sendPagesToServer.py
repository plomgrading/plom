#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2019 Andrew Rechnitzer and Colin Macdonald"
__credits__ = ["Andrew Rechnitzer", "Colin Macdonald"]
__license__ = "AGPL-3.0-or-later"
# SPDX-License-Identifier: AGPL-3.0-or-later

from glob import glob
import getpass
import hashlib
import json
import os
import requests
from requests_toolbelt import MultipartEncoder
import shutil
import ssl
import sys
import urllib3
import toml
import threading

# ----------------------
from plom_exceptions import *

sys.path.append("..")
from version import Plom_API_Version

_userName = "scanner"

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


def requestAndSaveToken(user, pw):
    """Get a authorisation token from the server.

    The token is then used to authenticate future transactions with the server.

    """
    global _userName, _token

    SRmutex.acquire()
    try:
        print("Requesting authorisation token from server")
        response = authSession.put(
            "https://{}:{}/users/{}".format(server, message_port, user),
            json={"user": user, "pw": pw, "api": Plom_API_Version},
            verify=False,
            timeout=5,
        )
        # throw errors when response code != 200.
        response.raise_for_status()
        # convert the content of the response to a textfile for identifier
        _token = response.json()
        _userName = user
        print("Success!")
    except requests.HTTPError as e:
        if response.status_code == 401:  # authentication error
            print(
                "Password problem - you are not authorised to upload pages to server."
            )
        elif response.status_code == 400:  # API error
            raise PlomAPIException()
            print("An API problem - {}".format(response.json()))
        else:
            raise PlomSeriousException("Some other sort of error {}".format(e))
        quit()
    except requests.ConnectionError as err:
        raise PlomSeriousException(
            "Cannot connect to\n server:port = {}:{}\n Please check details before trying again.".format(
                server, message_port
            )
        )
        quit()
    finally:
        SRmutex.release()


def closeUser():
    SRmutex.acquire()
    try:
        response = session.delete(
            "https://{}:{}/users/{}".format(server, message_port, _userName),
            json={"user": _userName, "token": _token},
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

    return True


# def getInfoGeneral():
#     SRmutex.acquire()
#     try:
#         response = session.get(
#             "https://{}:{}/info/general".format(server, message_port), verify=False,
#         )
#         response.raise_for_status()
#         pv = response.json()
#     except requests.HTTPError as e:
#         if response.status_code == 404:
#             raise PlomSeriousException(
#                 "Server could not find the spec - this should not happen!"
#             )
#         else:
#             raise PlomSeriousException("Some other sort of error {}".format(e))
#     finally:
#         SRmutex.release()
#
#     fields = (
#         "testName",
#         "numberOfTests",
#         "numberOfPages",
#         "numberOfQuestions",
#         "numberOfVersions",
#         "publicCode",
#     )
#     return dict(zip(fields, pv))


def uploadKnownPage(code, test, page, version, sname, fname, md5sum):
    SRmutex.acquire()
    try:
        param = {
            "user": _userName,
            "token": _token,
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
            json={"user": _userName, "token": _token,},
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


def buildDirectories():
    """Build the directories that this script needs"""
    # the list of directories. Might need updating.
    lst = ["sentPages", "discardedPages", "collidingPages"]
    for dir in lst:
        try:
            os.mkdir(dir)
        except FileExistsError:
            pass


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
        shutil.move(fname, "sentPages/{}".format(shortName))
        shutil.move(
            fname + ".qr", "sentPages/{}.qr".format(shortName),
        )
    else:  # msg = [False, reason, message]
        print(rmsg[1], rmsg[2])
        if rmsg[1] == "duplicate":
            shutil.move(fname, "discardedPages/{}".format(shortName))
            shutil.move(fname + ".qr", "discardedPages/{}.qr".format(shortName))

        elif rmsg[1] == "collision":
            nname = "collidingPages/{}".format(shortName)
            shutil.move(fname, nname)
            shutil.move(fname + ".qr", nname + ".qr".format(shortName))
            # and write the name of the colliding file
            with open(nname + ".collide", "w+") as fh:
                json.dump(rmsg[2], fh)  # this is [collidingFile, test, page, version]
        # now bad errors
        elif rmsg[1] == "testError":
            print("This should not happen - todo = log error in sensible way")
        elif rmsg[1] == "pageError":
            print("This should not happen - todo = log error in sensible way")


def sendKnownFiles(fileList):
    for fname in fileList:
        shortName = os.path.split(fname)[1]
        ts, ps, vs = extractTPV(shortName)
        print("Upload {},{},{} = {} to server".format(ts, ps, vs, shortName))
        md5 = hashlib.md5(open(fname, "rb").read()).hexdigest()
        code = "t{}p{}v{}".format(ts.zfill(4), ps.zfill(2), vs)
        rmsg = uploadKnownPage(code, int(ts), int(ps), int(vs), shortName, fname, md5)
        doFiling(rmsg, ts, ps, vs, shortName, fname)


def getServerInfo():
    global server
    global message_port
    if os.path.isfile("server.toml"):
        with open("server.toml") as fh:
            si = toml.load(fh)
        server = si["server"]
        message_port = si["port"]


if __name__ == "__main__":
    getServerInfo()
    print("Uploading to {} port {}".format(server, message_port))
    try:
        pwd = getpass.getpass("Please enter the 'scanner' password:")
    except Exception as error:
        print("ERROR", error)

    authSession = requests.Session()
    authSession.mount("https://", requests.adapters.HTTPAdapter(max_retries=3))
    requestAndSaveToken("scanner", pwd)

    session = requests.Session()
    session.mount("https://", requests.adapters.HTTPAdapter(max_retries=50))

    buildDirectories()

    # Look for pages in decodedPages
    fileList = glob("decodedPages/t*.png")
    sendKnownFiles(fileList)
    closeUser()
