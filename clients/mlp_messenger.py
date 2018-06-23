import sys, os, json
from os import path
import easywebdav2, asyncio, ssl

from gui_utils import ErrorMessage

from PyQt5.QtCore import QElapsedTimer


webdav_user = 'hack'
webdav_passwd = 'duhbah'
sslContext = ssl.create_default_context(purpose=ssl.Purpose.CLIENT_AUTH)
sslContext.check_hostname = False

server=None
message_port=None
def setServerDetails(s,mp,dp):
    global server, message_port, webdav_port
    server = s
    message_port=mp
    webdav_port=dp


async def handle_messaging(msg):
    reader, writer = await asyncio.open_connection(server, message_port, loop=loop, ssl=sslContext)
    print("Sending message {}",format(msg))
    jm = json.dumps(msg)
    writer.write(jm.encode())
    # SSL does not support EOF, so send a null byte to indicate the end of the message.
    writer.write(b'\x00')
    await writer.drain()

    data = await reader.read(100)
    terminate = data.endswith(b'\x00')
    data = data.rstrip(b'\x00')
    rmesg = json.loads( data.decode() ) # message should be a list [cmd, user, arg1, arg2, etc]
    writer.close()
    print("Got message {}".format(rmesg))
    return(rmesg)

def SRMsg(msg):
    rmsg = loop.run_until_complete(handle_messaging(msg))
    if( rmsg[0] == 'ACK'):
        return(rmsg)
    elif( rmsg[0] == 'ERR'):
        msg = ErrorMessage(rmsg[1])
        msg.exec_()
        return(rmsg)
    else:
        msg = ErrorMessage("Something really wrong has happened.")
        self.Close()

def getFileDav(dfn, lfn):
  webdav = easywebdav2.connect(server, port=webdav_port, username=webdav_user, password=webdav_passwd)
  try:
    argh = webdav.download(dfn,lfn)
  except Exception as ex:
    template = "An exception of type {0} occurred. Arguments:\n{1!r}"
    message = template.format(type(ex).__name__, ex.args)
    print( message)

def putFileDav(lfn,dfn):
  webdav = easywebdav2.connect(server, port=webdav_port, username=webdav_user, password=webdav_passwd)
  try:
    argh = webdav.upload(lfn,dfn)
  except Exception as ex:
    template = "An exception of type {0} occurred. Arguments:\n{1!r}"
    message = template.format(type(ex).__name__, ex.args)
    print( message)

def startMessenger():
    global loop
    print("Starting asyncio loop")
    loop = asyncio.get_event_loop()

def stopMessenger():
    loop.close()
    print("Stopped asyncio loop")
