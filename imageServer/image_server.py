import asyncio
import datetime
import errno
import glob
import json
import logging
import os
import shlex
import socket
import ssl
import subprocess
import sys
import tempfile

from id_storage import *
from mark_storage import *
from authenticate import *

sys.path.append('..')  # this allows us to import from ../resources
from resources.testspecification import TestSpecification

# # # # # # # # # # # #
# For setting up separate logging for IDing and Marking
def setupLogger(name, log_file, level=logging.INFO):
    # https://stackoverflow.com/questions/11232230/logging-to-two-files-with-different-settings
    """Function setup as many loggers as you want"""
    logging.basicConfig(format='%(asctime)s %(message)s', datefmt='%d/%m/%Y %I:%M:%S %p')
    handler = logging.FileHandler(log_file)
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(handler)
    return logger

# # # # # # # # # # # #
# default values.

serverInfo = {'server': '127.0.0.1', 'mport': 41984, 'wport': 41985}

# # # # # # # # # # # #

pathScanDirectory = "../scanAndGroup/readyForMarking/"

# # # # # # # # # # # #

sslContext = ssl.create_default_context(purpose=ssl.Purpose.CLIENT_AUTH)
sslContext.check_hostname = False
sslContext.load_cert_chain('../resources/mlp-selfsigned.crt', '../resources/mlp.key')


# # # # # # # # # # # #
# These functions need improving - read from the JSON files
def readExamsGrouped():
    global examsGrouped
    if os.path.exists("../resources/examsGrouped.json"):
        with open('../resources/examsGrouped.json') as data_file:
            examsGrouped = json.load(data_file)
            for n in examsGrouped.keys():
                print("Adding id group {}".format(examsGrouped[n][0]))


def findPageGroups():
    global pageGroupsForGrading
    for pg in range(1, spec.getNumberOfGroups()+1):
        for fname in glob.glob("{}/group_{}/*/*.png".format(pathScanDirectory, str(pg).zfill(2))):
            print("Adding pageimage from {}".format(fname))
            pageGroupsForGrading[os.path.basename(fname)[:-4]] = fname


def getServerInfo():
    global serverInfo
    if os.path.isfile("../resources/serverDetails.json"):
        with open('../resources/serverDetails.json') as data_file:
            serverInfo = json.load(data_file)
            print("Server details loaded: ", serverInfo)
    else:
        print("Cannot find server details.")


# # # # # # # # # # # #

servCmd = {'AUTH': 'authoriseUser', 'UCL': 'userClosing', 'iDNF': 'IDdidntFinish', 'iNID': 'IDnextUnIDd', 'iGTP': 'IDgotTest', 'iPRC': 'IDProgressCount', 'iRID': 'IDreturnIDd', 'iRAD': 'IDreturnAlreadyIDd', 'iRCL': 'IDrequestClassList', 'iGCL': 'IDgotClassList', 'mDNF': 'MdidntFinish', 'mNUM': 'MnextUnmarked', 'mGTP': 'MgotTest', 'mPRC': 'MProgressCount', 'mRMD': 'MreturnMarked', 'mRAM': 'MreturnAlreadyMarked', 'mGMX': 'MgetPageGroupMax'}


async def handle_messaging(reader, writer):
    data = await reader.read(128)
    terminate = data.endswith(b'\x00')
    data = data.rstrip(b'\x00')
    message = json.loads(data.decode())  # message should be a list [cmd, user, password, arg1, arg2, etc]
    print("Got message {}".format(message))

    if not isinstance(message, list):
        print("Some sort of message error here - didn't receive a list.")
    else:
        rmesg = peon.proc_cmd(message)

    print("Returning message {}".format(rmesg))

    addr = writer.get_extra_info('peername')
    jdm = json.dumps(rmesg)
    writer.write(jdm.encode())
    # SSL does not support EOF, so send a null byte to indicate the end of the message.
    writer.write(b'\x00')
    await writer.drain()
    writer.close()


# # # # # # # # # # # #
# # # # # # # # # # # #
def splitTGV(tgv):  # t1234g67v9
    return(int(tgv[1:5]), int(tgv[6:8]), int(tgv[9]))


class Server(object):
    def __init__(self, id_db, mark_db, tspec):
        self.IDDB = id_db
        self.MDB = mark_db
        self.testSpec = tspec

        self.loadPapers()
        self.loadUsers()

    def loadUsers(self):
        if os.path.exists("../resources/userList.json"):
            with open('../resources/userList.json') as data_file:
                self.userList = json.load(data_file)
                self.authority = Authority(self.userList)
                print("Users = {}".format(list(self.userList.keys())))
        else:
            print("Where is user/password file?")
            quit()

    def reloadImages(self, password):
        if not self.authority.authoriseUser('Manager', password):
            return(['ERR', 'You are not authorised to reload images'])

        readExamsGrouped()
        findPageGroups()
        self.loadPapers()
        return ['ACK']

    def reloadUsers(self, password):
        if not self.authority.authoriseUser('Manager', password):
            return(['ERR', 'You are not authorised to reload users'])
        if os.path.exists("../resources/userList.json"):
            with open('../resources/userList.json') as data_file:
                newUserList = json.load(data_file)
                for u in newUserList:
                    if u not in self.userList:
                        self.userList[u] = newUserList[u]
                        self.authority.addUser(u, newUserList[u])
                        print("New user = {}".format(u))
                for u in self.userList:
                    if u not in newUserList:
                        print("Removing user = {}".format(u))
                        self.IDDB.resetUsersToDo(u)
                        self.MDB.resetUsersToDo(u)
                        self.authority.detoken(u)
        print("Current user list = {}".format(list(self.userList.keys())))
        return ['ACK']

    def proc_cmd(self, message):
        pcmd = servCmd.get(message[0], 'msgError')

        if message[0] == 'PING':
            # Return an ack if a ping is sent.
            return ['ACK']
        elif message[0] == 'AUTH':
            # message should be ['AUTH', user, password]
            return self.authoriseUser(*message[1:])
        elif message[0] == 'RUSR':
            # message should be ['RUSR', managerpwd]
            rv = self.reloadUsers(*message[1:])
            return rv
        elif message[0] == 'RIMR':
            # message should be ['RIMR', managerpwd]
            rv = self.reloadImages(*message[1:])
            return rv
        else:
            # should be ['CMD', user, token, arg1, arg2,...]
            if self.validate(message[1], message[2]):
                return getattr(self, pcmd)(*message[1:])
            else:
                print("Attempt by non-user to {}".format(message))
                return(['ERR', 'You are not an authorised user'])

    def authoriseUser(self, user, password):
        if self.authority.authoriseUser(user, password):
            # On token request also make sure anything "out" with that user is reset as todo.
            self.IDDB.resetUsersToDo(user)
            self.MDB.resetUsersToDo(user)
            return ['ACK', self.authority.getToken(user)]
        else:
            return ['ERR', 'You are not an authorised user']

    def validate(self, user, token):
        if self.authority.validateToken(user, token):
            return True
        else:
            return False

    def loadPapers(self):
        # Needs improvement
        print("Adding IDgroups {}".format(sorted(examsGrouped.keys())))
        for t in sorted(examsGrouped.keys()):
            self.IDDB.addUnIDdExam(int(t), "t{:s}idg".format(t.zfill(4)))

        print("Adding TGVs {}".format(sorted(pageGroupsForGrading.keys())))
        for tgv in sorted(pageGroupsForGrading.keys()):
            t, pg, v = splitTGV(tgv)
            self.MDB.addUnmarkedGroupImage(t, pg, v, tgv, pageGroupsForGrading[tgv])

    def provideFile(self, fname):
        tfn = tempfile.NamedTemporaryFile(delete=False, dir=davDirectory)
        os.system("cp " + fname + " " + tfn.name)
        return os.path.basename(tfn.name)

    def claimFile(self, fname):
        os.system("mv " + davDirectory + "/" + fname + " ./markedPapers/")

    def removeFile(self, davfn):
        os.remove(davDirectory+"/"+davfn)

    def printToDo(self):
        self.IDDB.printToDo()
        self.MDB.printToDo()

    def printOutForMarking(self):
        self.MDB.printOutForMarking()

    def printOutForIDing(self):
        self.IDDB.printOutForIDing()

    def printMarked(self):
        self.MDB.printIdentified()

    def printIdentified(self):
        self.IDDB.printIdentified()

    def msgError(self, *args):
        return ['ERR', 'Some sort of command error - what did you send?']

    def IDrequestClassList(self, user, token):
        return ['ACK', self.provideFile("../resources/classlist.csv")]

    def IDgotClassList(self, user, token, tfn):
        self.removeFile(tfn)
        return ['ACK']

    def MgetPageGroupMax(self, user, token, pg, v):
        iv = int(v)
        ipg = int(pg)
        if ipg < 1 or ipg > self.testSpec.getNumberOfGroups():
            return ['ERR', 'Pagegroup out of range']
        if iv < 1 or iv > self.testSpec.Versions:
            return ['ERR', 'Version out of range']
        return ['ACK', self.testSpec.Marks[ipg]]

    def IDdidntFinish(self, user, token, code):
        self.IDDB.didntFinish(user, code)
        self.IDDB.saveIdentified()
        return ['ACK']

    def MdidntFinish(self, user, token, tgv):
        self.MDB.didntFinish(user, tgv)
        self.MDB.saveMarked()
        return ['ACK']

    def userClosing(self, user, token):
        self.authority.detoken(user)
        return ['ACK']

    def IDnextUnIDd(self, user, token):
        give = self.IDDB.giveIDImageToClient(user)
        if give is None:
            return ['ERR', 'No more papers']
        else:
            return ['ACK', give, self.provideFile("{}/idgroup/{}.png".format(pathScanDirectory, give))]

    def IDProgressCount(self, user, token):
        return ['ACK', self.IDDB.countIdentified(), self.IDDB.countAll()]

    def IDgotTest(self, user, token, test, tfn):
        self.removeFile(tfn)
        return ['ACK']

    def IDreturnIDd(self, user, token, ret, sid, sname):
        if self.IDDB.takeIDImageFromClient(ret, user, sid, sname):
            return ['ACK']
        else:
            return ['ERR', 'That student number already used.']

    def IDreturnAlreadyIDd(self, user, token, ret, sid, sname):
        self.IDDB.takeIDImageFromClient(ret, user, sid, sname)
        return ['ACK']

    def MnextUnmarked(self, user, token, pg, v):
        give, fname = self.MDB.giveGroupImageToClient(user, pg, v)
        if give is not None:
            return ['ACK', give, self.provideFile(fname)]
        else:
            return ['ERR', 'Nothing left on todo pile']

    def MProgressCount(self, user, token, pg, v):
        return['ACK', self.MDB.countMarked(pg, v), self.MDB.countAll(pg, v)]

    def MgotTest(self, user, token, tfn):
        self.removeFile(tfn)
        return ['ACK']

    def MreturnMarked(self, user, token, code, mark, fname, mtime):
        # move annoted file to right place with new filename
        self.MDB.takeGroupImageFromClient(code, user, mark, fname, mtime)
        self.recordMark(user, mark, fname, mtime)
        self.claimFile(fname)
        return ['ACK']

    def recordMark(self, user, mark, fname, mtime):
        fh = open("./markedPapers/{}.txt".format(fname), 'w')
        fh.write("{}\t{}\t{}\t{}\t{}".format(fname, mark, user, datetime.now().strftime("%Y-%m-%d,%H:%M"), mtime))
        fh.close()


# # # # # # # # # # # #
# # # # # # # # # # # #

def checkPortFree(ip, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind((ip, port))
    except socket.error as err:
        if err.errno == errno.EADDRINUSE:
            return False
        else:
            print("There is some sort of ip/port error. Number = {}".format(err.errno))
            return False
    return True


def checkPorts():
    if checkPortFree(serverInfo['server'], serverInfo['mport']):
        print("Messaging port is free and working.")
    else:
        print("Problem with messaging port {} on server {}. Please check and try again.".format(serverInfo['mport'], serverInfo['server']))
        exit()

    if checkPortFree(serverInfo['server'], serverInfo['wport']):
        print("Webdav port is free and working.")
    else:
        print("Problem with webdav port {} on server {}. Please check and try again.".format(serverInfo['wport'], serverInfo['server']))
        exit()


getServerInfo()
checkPorts()

tempDirectory = tempfile.TemporaryDirectory()
davDirectory = tempDirectory.name
os.system("chmod o-r {}".format(davDirectory))
print("Dav = {}".format(davDirectory))
cmd = "wsgidav -q -H {} -p {} --server cheroot -r {} -c ../resources/davconf.conf".format(serverInfo['server'], serverInfo['wport'], davDirectory)
davproc = subprocess.Popen(shlex.split(cmd))

spec = TestSpecification()
spec.readSpec()
examsGrouped = {}
readExamsGrouped()
pageGroupsForGrading = {}
findPageGroups()

# Set up loggers for marking and ID-ing
IDLogger = setupLogger("IDLogger", "identity_storage.log")
MarkLogger = setupLogger("MarkLogger", "mark_storage.log")
# Set up the classes for handling transactions with databases
# Pass them the loggers
theIDDB = IDDatabase(IDLogger)
theMarkDB = MarkDatabase(MarkLogger)
# Fire up the server with both database client classes and the test-spec.
peon = Server(theIDDB, theMarkDB, spec)

# # # # # # # # # # # #

loop = asyncio.get_event_loop()
coro = asyncio.start_server(handle_messaging, serverInfo['server'], serverInfo['mport'], loop=loop, ssl=sslContext)
try:
    server = loop.run_until_complete(coro)
except OSError:
    print("There is a problem running the socket-listening loop. Check if port {} is free and try again.".format(serverInfo['mport']))
    subprocess.Popen.kill(davproc)
    loop.close()
    exit()

print('Serving messages on {}'.format(server.sockets[0].getsockname()))
try:
    loop.run_forever()
except KeyboardInterrupt:
    pass

server.close()
loop.run_until_complete(server.wait_closed())
loop.close()

# # # # # # # # # # # #

subprocess.Popen.kill(davproc)
print("Webdav server closed")
theIDDB.saveIdentified()
theMarkDB.saveMarked()
