import hashlib
import os
import uuid


def IDprogressCount(self):
    """Send back current ID progress counts to the client"""
    return [self.DB.IDcountIdentified(), self.DB.IDcountAll()]


def IDaskNextTask(self):
    # Get number of next unidentified test from the database
    give = self.DB.IDaskNextTask(user)
    if give is None:
        return [False]
    else:
        return [True, give]


def IDrequestDoneTasks(self, user):
    """When a id-client logs on they request a list of papers they have already IDd.
    Send back the list.
    """
    return self.DB.IDbuildIDList(user)
