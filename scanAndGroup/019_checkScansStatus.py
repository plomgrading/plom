#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2020 Andrew Rechnitzer and Colin Macdonald"
__credits__ = ["Andrew Rechnitzer", "Colin Macdonald"]
__license__ = "AGPL-3.0-or-later"
# SPDX-License-Identifier: AGPL-3.0-or-later

import requests
import shutil
import ssl
import sys
import urllib3
import threading

# ----------------------
sys.path.append("..")
from resources.specParser import SpecParser
from resources.plom_exceptions import *
from resources.misc_utils import format_int_list_with_runs

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


def getScannedTests():
    SRmutex.acquire()
    try:
        response = session.get(
            "https://{}:{}/REP/scanned".format(server, message_port), verify=False,
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


def getUnusedTests():
    SRmutex.acquire()
    try:
        response = session.get(
            "https://{}:{}/REP/unused".format(server, message_port), verify=False,
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


def getIncompleteTests():
    SRmutex.acquire()
    try:
        response = session.get(
            "https://{}:{}/REP/incomplete".format(server, message_port), verify=False,
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

if __name__ == "__main__":
    spec = SpecParser().spec
    session = requests.Session()
    session.mount("https://", requests.adapters.HTTPAdapter(max_retries=50))

    ST = getScannedTests()
    UT = getUnusedTests()
    IT = getIncompleteTests()
    print("Test papers unused: [{}]".format(format_int_list_with_runs(UT)))

    print("Scanned tests in the system: [{}]".format(format_int_list_with_runs(ST)))

    print("Incomplete scans - listed by their missing pages: ")
    for t in IT:
        print("\t{}: [{}]".format(t, format_int_list_with_runs(IT[t])))
