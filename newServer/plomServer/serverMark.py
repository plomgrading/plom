import hashlib
import os
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
