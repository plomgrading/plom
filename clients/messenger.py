__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2018-2019 Andrew Rechnitzer"
__credits__ = ["Andrew Rechnitzer", "Colin Macdonald", "Elvis Cai", "Matt Coles"]
__license__ = "AGPLv3"

import asyncio
import requests
import easywebdav2
import json
import ssl
from PyQt5.QtWidgets import QMessageBox
import urllib3
from useful_classes import ErrorMessage

# If we use unverified ssl certificates we get lots of warnings,
# so put in this to hide them.
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
sslContext = ssl.create_default_context(purpose=ssl.Purpose.CLIENT_AUTH)
sslContext.check_hostname = False
# Server defaults
server = "127.0.0.1"
message_port = 41984
webdav_port = 41985


def setServerDetails(s, mp, dp):
    """Set the server IP, message port and webdav port"""
    global server, message_port, webdav_port
    server = s
    message_port = mp
    webdav_port = dp


def http_messaging(msg):
    response = session.put(
        "https://localhost:{}/".format(message_port), json={"msg": msg}, verify=False
    )
    print(response.text)
    return response.json()["rmsg"]


def SRMsgHTTPS(msg):
    """Send message using https and get back return message.
    If error then pop-up an error message.
    """
    rmsg = http_messaging(msg)
    if rmsg[0] == "ACK":
        return rmsg
    elif rmsg[0] == "ERR":
        msg = ErrorMessage("Server says: " + rmsg[1])
        msg.exec_()
        return rmsg
    else:
        print(">>> Error I didn't expect. Return message was {}".format(rmsg))
        msg = ErrorMessage("Something really wrong has happened.")
        msg.exec_()


async def handle_messaging(msg):
    """Asyncio messager handler.
    Sends message over the connection.
    Message should be a list [cmd, user, password, arg1, arg2, etc]
    Reads return message from the stream - usually ['ACK', arg1, arg2,...]
    """
    reader, writer = await asyncio.open_connection(
        server, message_port, loop=loop, ssl=sslContext
    )
    # Message should be  [cmd, user, password, arg1, arg2, etc]
    jm = json.dumps(msg)
    writer.write(jm.encode())
    # SSL does not support EOF, so send a null byte to indicate the end
    # of the message.
    writer.write(b"\x00")
    await writer.drain()

    # data = await reader.read(100)
    data = await reader.readline()
    terminate = data.endswith(b"\x00")
    data = data.rstrip(b"\x00")
    rmesg = json.loads(data.decode())  # message should be a list [ACK, arg1, arg2, etc]
    writer.close()
    return rmesg


def SRMsg(msg):
    """Send message using the asyncio message handler and get back
    return message. If error then pop-up an error message.
    """
    return SRMsgHTTPS(msg)

    rmsg = loop.run_until_complete(handle_messaging(msg))
    if rmsg[0] == "ACK":
        return rmsg
    elif rmsg[0] == "ERR":
        msg = ErrorMessage("Server says: " + rmsg[1])
        msg.exec_()
        return rmsg
    else:
        print(">>> Error I didn't expect. Return message was {}".format(rmsg))
        msg = ErrorMessage("Something really wrong has happened.")
        msg.exec_()


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


async def handle_ping_test():
    """ A simple ping to test if the server is up and running.
    If nothing back after 2 seconds then assume the server is
    down and tell the user, then exit.
    """
    ptest = asyncio.open_connection(server, message_port, loop=loop, ssl=sslContext)
    try:
        # Wait for 2 seconds, then raise TimeoutError
        reader, writer = await asyncio.wait_for(ptest, timeout=2)
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
    except (asyncio.TimeoutError, ConnectionRefusedError, OSError):
        msg = ErrorMessage(
            "Server does not return ping." " Please double check details and try again."
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
    # """Start the asyncio event loop"""
    # global loop
    # print("Starting asyncio loop")
    # loop = asyncio.get_event_loop()

    print("Starting a requests-session")
    global session
    session = requests.Session()
    session.mount("https://", requests.adapters.HTTPAdapter(max_retries=50))


def stopMessenger():
    """Stop the asyncio event loop"""
    loop.close()
    print("Stopped asyncio loop")
    session.close()
