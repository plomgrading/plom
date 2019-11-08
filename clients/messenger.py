# -*- coding: utf-8 -*-

"""
Backend bits n bobs to talk to the server
"""

__author__ = "Andrew Rechnitzer, Colin B. Macdonald"
__copyright__ = "Copyright (C) 2018-2019 Andrew Rechnitzer, Colin B. Macdonald"
__credits__ = ["Andrew Rechnitzer", "Colin Macdonald", "Elvis Cai", "Matt Coles"]
__license__ = "AGPL-3.0-or-later"
# SPDX-License-Identifier: AGPL-3.0-or-later

import sys
import asyncio
import requests
import easywebdav2
import json
import ssl
from PyQt5.QtWidgets import QMessageBox
import urllib3
from useful_classes import ErrorMessage
import time
import threading

sys.path.append("..")  # this allows us to import from ../resources
from resources.version import Plom_API_Version

# If we use unverified ssl certificates we get lots of warnings,
# so put in this to hide them.
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
sslContext = ssl.create_default_context(purpose=ssl.Purpose.CLIENT_AUTH)
sslContext.check_hostname = False
# Server defaults
server = "127.0.0.1"
message_port = 41984
webdav_port = 41985
SRmutex = threading.Lock()
_userName = None
_token = None


def setServerDetails(s, mp, dp):
    """Set the server IP, message port and webdav port"""
    global server, message_port, webdav_port
    server = s
    message_port = mp
    webdav_port = dp


def whoami():
    global _userName
    return _userName


def http_messaging(msg):
    try:
        response = session.put(
            "https://{}:{}/".format(server, message_port),
            json={"msg": msg},
            verify=False,
        )
    except:
        return [
            "ERR",
            "Something went seriously wrong. Check connection details and try again.",
        ]
    return response.json()["rmsg"]


def requestAndSaveToken(user, pw):
    """Get a authorisation token from the server

    The request sends name and password (over ssl) to the server. If
    hash of password matches the one on file, then the server sends
    back an "ACK" and an authentication token. The token is then used
    to authenticate future transactions with the server (since
    password hashing is slow).

    Raise a ValueError with message from the server.

    TODO: what happens on timeout?
    """
    global _userName, _token

    msg = ("AUTH", user, pw, Plom_API_Version)
    with SRmutex:
        rmsg = http_messaging(msg)

    if rmsg[0] == "ACK" and len(rmsg) == 2:
        _userName = user
        _token = rmsg[1]
        return
    elif rmsg[0] == "ERR" and len(rmsg) == 2:
        raise ValueError(rmsg[1])
    else:
        raise RuntimeError(
            "Unexpected response from server.  Consider filing a bug?  The return from the server was:\n\n"
            + str(rmsg)
        )


def msg(msgcode, *args):
    """Send message using https and get back return message.
    If error then pop-up an error message.
    """
    msg_ = (msgcode, _userName, _token, *args)
    SRmutex.acquire()
    try:
        rmsg = http_messaging(msg_)
    finally:
        SRmutex.release()

    if rmsg[0] == "ACK":
        return rmsg
    elif rmsg[0] == "ERR":
        ErrorMessage("Server says: " + rmsg[1]).exec_()
        return rmsg
    else:
        print(">>> Error I didn't expect. Return message was {}".format(rmsg))
        ErrorMessage("Something really wrong has happened.").exec_()


def msg_nopopup(msgcode, *args):
    """Send message using the asyncio message handler and get back
    return message.
    """
    msg = (msgcode, _userName, _token, *args)
    SRmutex.acquire()
    try:
        rmsg = http_messaging(msg)
    finally:
        SRmutex.release()

    if rmsg[0] in ("ACK", "ERR"):
        return rmsg
    else:
        raise RuntimeError(
            "Unexpected response from server.  Consider filing a bug?  The return from the server was:\n\n"
            + str(rmsg)
        )


def getFileDav(dfn, lfn):
    """Get file dfn from the webdav server and save as lfn."""
    webdav = easywebdav2.connect(
        server, port=webdav_port, protocol="https", verify_ssl=False
    )
    try:
        webdav.download(dfn, lfn)
    except Exception as ex:
        template = ">>> An exception of type {0} occurred. Arguments:\n{1!r}"
        message = template.format(type(ex).__name__, ex.args)
        print(message)


def putFileDav(lfn, dfn):
    """Upload file lfn to the webdav as dfn."""
    webdav = easywebdav2.connect(
        server, port=webdav_port, protocol="https", verify_ssl=False
    )
    try:
        webdav.upload(lfn, dfn)
    except Exception as ex:
        template = ">>> An exception of type {0} occurred. Arguments:\n{1!r}"
        message = template.format(type(ex).__name__, ex.args)
        print(message)


def getFileDav_woInsanity(dfn, lfn):
    """Get file dfn from the webdav server and save as lfn.

    Does not do anything for exceptions: that's the caller's problem.
    """
    webdav = easywebdav2.connect(
        server, port=webdav_port, protocol="https", verify_ssl=False
    )
    webdav.download(dfn, lfn)


def putFileDav_woInsanity(lfn, dfn):
    """Upload file lfn to the webdav as dfn.

    Does not do any exception handling: that's the caller's problem.
    """
    webdav = easywebdav2.connect(
        server, port=webdav_port, protocol="https", verify_ssl=False
    )
    webdav.upload(lfn, dfn)


async def handle_ping_test():
    """ A simple ping to test if the server is up and running.
    If nothing back after a few seconds then assume the server is
    down and tell the user, then exit.
    """
    ptest = asyncio.open_connection(server, message_port, loop=loop, ssl=sslContext)
    try:
        reader, writer = await asyncio.wait_for(ptest, timeout=6)
        jm = json.dumps(["PING"])
        writer.write(jm.encode())
        writer.write(b"\x00")
        await writer.drain()

        data = await reader.read(100)
        terminate = data.endswith(b"\x00")
        data = data.rstrip(b"\x00")
        rmesg = json.loads(data.decode())  # message should be ['ACK']
        writer.close()
        return True
    except asyncio.TimeoutError as e:
        # TODO: str(e) does nothing useful to keep separate from below
        msg = ErrorMessage(
            "Server timed out.  " "Please double check details and try again."
        )
        msg.exec_()
        return False
    except (ConnectionRefusedError, OSError) as e:
        msg = ErrorMessage(
            "Server does not return ping.  "
            "Please double check details and try again.\n\n"
            "Details:\n" + str(e)
        )
        msg.exec_()
        return False


def pingTest():
    """Use the asyncio handler to send a ping to the server
    to check it is up and running
    """
    rmsg = loop.run_until_complete(handle_ping_test())
    return rmsg


session = None


def startMessenger():
    """Start the asyncio event loop"""
    print("Starting a requests-session")
    global session
    session = requests.Session()
    # set max_retries to large number because UBC-wifi is pretty crappy.
    # TODO - set smaller number and have some sort of "hey you've retried
    # nn times already, are you sure you want to keep retrying" message.
    session.mount("https://", requests.adapters.HTTPAdapter(max_retries=50))


def stopMessenger():
    """Stop the asyncio event loop"""
    loop.close()
    print("Stopped asyncio loop")
    session.close()
