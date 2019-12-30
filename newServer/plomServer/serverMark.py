import hashlib
import os
import subprocess
import tempfile
import uuid


def MgetQuestionMax(self, q, v):
    iv = int(v)
    iq = int(q)
    # check question /version in range.
    if iq < 1 or iq > self.testSpec["numberOfQuestions"]:
        return [False, "QE"]
    if iv < 1 or iv > self.testSpec["numberOfVersions"]:
        return [False, "VE"]
    # Send back the max-mark for that q/v
    return [True, self.testSpec["question"][str(iq)]["mark"]]


def MprogressCount(self, q, v):
    """Send back current ID progress counts to the client"""
    iv = int(v)
    iq = int(q)
    return [self.DB.McountMarked(iq, iv), self.DB.McountAll(iq, iv)]


def MgetDoneTasks(self, user, q, v):
    """When a marked-client logs on they request a list of papers they have already marked.
    Check the (group/version) is valid and then send back a textfile with list of TGVs.
    """
    iv = int(v)
    iq = int(q)
    return self.DB.MgetDoneTasks(user, iq, iv)


def MgetNextTask(self, q, v):
    """The client has asked for the next unmarked paper, so
    ask the database for its code and send back to the
    client.
    """
    give = self.DB.MgetNextTask(q, v)
    if give is None:
        return [False]
    else:
        return [True, give]


def MlatexFragment(self, user, fragment):
    # TODO - only one frag file per user - is this okay?
    tfrag = tempfile.NamedTemporaryFile()
    with open(tfrag.name, "w+") as fh:
        fh.write(fragment)

    fname = os.path.join(self.tempDirectory.name, "{}_frag.png".format(user))
    if subprocess.run(["python3", "latex2png.py", tfrag.name, fname]).returncode == 0:
        return [True, fname]
    else:
        return [False]
