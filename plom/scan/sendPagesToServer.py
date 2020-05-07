#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2019 Andrew Rechnitzer and Colin Macdonald"
__credits__ = ["Andrew Rechnitzer", "Colin Macdonald"]
__license__ = "AGPL-3.0-or-later"
# SPDX-License-Identifier: AGPL-3.0-or-later

from collections import defaultdict
from glob import glob
import getpass
import hashlib
import json
import os
import shutil
import sys
import toml

from plom.messenger import ScanMessenger
from plom.plom_exceptions import *
from plom import PlomImageExtWhitelist
from plom.rules import isValidStudentNumber


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
        shutil.move(fname, os.path.join("sentPages", shortName))
        shutil.move(fname + ".qr", os.path.join("sentPages", shortName + ".qr"))
    else:  # msg = [False, reason, message]
        print(rmsg[1], rmsg[2])
        if rmsg[1] == "duplicate":
            shutil.move(fname, os.path.join("discardedPages", shortName))
            shutil.move(
                fname + ".qr", os.path.join("discardedPages", shortName + ".qr")
            )

        elif rmsg[1] == "collision":
            nname = os.path.join("collidingPages", shortName)
            shutil.move(fname, nname)
            shutil.move(fname + ".qr", nname + ".qr")
            # and write the name of the colliding file
            with open(nname + ".collide", "w+") as fh:
                json.dump(rmsg[2], fh)  # this is [collidingFile, test, page, version]
        # now bad errors
        elif rmsg[1] == "testError":
            print("This should not happen - todo = log error in sensible way")
        elif rmsg[1] == "pageError":
            print("This should not happen - todo = log error in sensible way")


def sendTestFiles(msgr, fileList):
    TUP = defaultdict(list)
    for fname in fileList:
        shortName = os.path.split(fname)[1]
        ts, ps, vs = extractTPV(shortName)
        print("Upload {},{},{} = {} to server".format(ts, ps, vs, shortName))
        md5 = hashlib.md5(open(fname, "rb").read()).hexdigest()
        code = "t{}p{}v{}".format(ts.zfill(4), ps.zfill(2), vs)
        rmsg = msgr.uploadTestPage(
            code, int(ts), int(ps), int(vs), shortName, fname, md5
        )
        doFiling(rmsg, ts, ps, vs, shortName, fname)
        if rmsg[0]:  # was successful upload
            TUP[ts].append(ps)
    return TUP


def extractIDQO(fileName):  # get ID, Question and Order
    """Expecting filename of the form blah.SID.Q-N.pdf - return SID Q and N"""
    splut = fileName.split(".")  # easy to get SID, and Q

    id = splut[-3]
    # split again, now on "-" to separate Q and N
    resplut = splut[-2].split("-")
    q = int(resplut[0])
    n = int(resplut[1])

    return (id, q, n)


def extractJIDO(fileName):  # get just ID, Order
    """Expecting filename of the form blah.SID-N.pdf - return SID and N"""

    splut = fileName.split(".")  # easy to get SID-N
    # split again, now on "-" to separate SID and N
    resplut = splut[-2].split("-")
    id = int(resplut[0])
    n = int(resplut[1])

    return (id, n)


def doHWFiling(shortName, fname):
    shutil.move(fname, os.path.join("sentPages", "submittedHWByQ", shortName))


def doXFiling(shortName, fname):
    shutil.move(fname, os.path.join("sentPages", "submittedHWOneFile", shortName))


def sendHWFiles(msgr, fileList):
    # keep track of which SID uploaded which Q.
    SIDQ = defaultdict(list)
    for fname in fileList:
        print("Upload hw page image {}".format(fname))
        shortName = os.path.split(fname)[1]
        sid, q, n = extractIDQO(shortName)
        print("Upload HW {},{},{} = {} to server".format(sid, q, n, shortName))
        md5 = hashlib.md5(open(fname, "rb").read()).hexdigest()
        rmsg = msgr.uploadHWPage(sid, q, n, shortName, fname, md5)
        if rmsg[0]:  # was successful upload
            doHWFiling(shortName, fname)
            SIDQ[sid].append(q)
    return SIDQ


def sendXFiles(msgr, fileList):
    # keep track of which SID uploaded.
    JSID = {}
    for fname in fileList:
        print("Upload hw page image {}".format(fname))
        shortName = os.path.split(fname)[1]
        sid, n = extractJIDO(shortName)

        print("Upload X {},{} = {} to server".format(sid, n, shortName))
        md5 = hashlib.md5(open(fname, "rb").read()).hexdigest()
        rmsg = msgr.uploadXPage(sid, n, shortName, fname, md5)
        if rmsg[0]:  # was successful upload
            doXFiling(shortName, fname)
            JSID[sid] = True
    return JSID


def uploadPages(server=None, password=None):
    if server and ":" in server:
        s, p = server.split(":")
        msgr = ScanMessenger(s, port=p)
    else:
        msgr = ScanMessenger(server)
    msgr.start()

    # get the password if not specified
    if password is None:
        try:
            pwd = getpass.getpass("Please enter the 'scanner' password:")
        except Exception as error:
            print("ERROR", error)
    else:
        pwd = password

    # get started
    try:
        msgr.requestAndSaveToken("scanner", pwd)
    except PlomExistingLoginException:
        print(
            "You appear to be already logged in!\n\n"
            "  * Perhaps a previous session crashed?\n"
            "  * Do you have another scanner-script running,\n"
            "    e.g., on another computer?\n\n"
            'In order to force-logout the existing authorisation run "plom-scan clear" or "plom-hwscan clear"'
        )
        exit(10)

    spec = msgr.getInfoGeneral()
    numberOfPages = spec["numberOfPages"]

    # Look for pages in decodedPages
    fileList = []
    for ext in PlomImageExtWhitelist:
        fileList.extend(sorted(glob("decodedPages/t*.{}".format(ext))))

    TUP = sendTestFiles(msgr, fileList)
    # we do not update any missing pages, since that is a serious issue for tests, and should not be done automagically

    updates = msgr.sendTUploadDone()

    msgr.closeUser()
    msgr.stop()

    return [TUP, updates]


def uploadHWPages(server=None, password=None):
    if server and ":" in server:
        s, p = server.split(":")
        msgr = ScanMessenger(s, port=p)
    else:
        msgr = ScanMessenger(server)
    msgr.start()

    # get the password if not specified
    if password is None:
        try:
            pwd = getpass.getpass("Please enter the 'scanner' password:")
        except Exception as error:
            print("ERROR", error)
    else:
        pwd = password

    # get started
    try:
        msgr.requestAndSaveToken("scanner", pwd)
    except PlomExistingLoginException:
        print(
            "You appear to be already logged in!\n\n"
            "  * Perhaps a previous session crashed?\n"
            "  * Do you have another scanner-script running,\n"
            "    e.g., on another computer?\n\n"
            'In order to force-logout the existing authorisation run "plom-hwscan clear"'
        )
        exit(10)

    # grab number of questions - so we can work out what is missing
    spec = msgr.getInfoGeneral()
    numberOfQuestions = spec["numberOfQuestions"]

    # Look for HWbyQ pages in decodedPages
    fileList = []
    for ext in PlomImageExtWhitelist:
        fileList.extend(sorted(glob("decodedPages/submittedHWByQ/*.{}".format(ext))))
    SIDQ = sendHWFiles(msgr, fileList)  # returns list of which SID did whic q.
    for sid in SIDQ:
        for q in range(1, numberOfQuestions + 1):
            if q not in SIDQ[sid]:
                print("SID {} missing question {}".format(sid, q))
                try:
                    msgr.replaceMissingHWQuestion(sid, q)
                except PlomTakenException:
                    print("That question already has pages. Skipping.")
    updates = msgr.sendHWUploadDone()

    # now look for HW OneFile in decodedPages
    fileList = []
    for ext in PlomImageExtWhitelist:
        fileList.extend(
            sorted(glob("decodedPages/submittedHWOneFile/*.{}".format(ext)))
        )
    SIDO = sendXFiles(msgr, fileList)  # returns list of which SID uploaded

    msgr.closeUser()
    msgr.stop()
    return [SIDQ, SIDO]
