import hashlib
import os
import uuid


def TgetMaxMark(self):
    tm = 0
    for q in range(self.testSpec["numberOfQuestions"]):
        tm += self.testSpec["question"][str(q + 1)]["mark"]
    return tm


def TprogressCount(self):
    """Send back current ID progress counts to the client"""
    return [self.DB.TcountTotalled(), self.DB.TcountAll()]


def TgetNextTask(self):
    # Get number of next untotalled test from the database
    give = self.DB.TgetNextTask()
    if give is None:
        return [False]
    else:
        return [True, give]


def TgetDoneTasks(self, user):
    """When a id-client logs on they request a list of papers they have already IDd.
    Send back the list.
    """
    return self.DB.TgetDoneTasks(user)


def TgetImage(self, username, testNumber):
    return self.DB.TgetImage(username, testNumber)


def TclaimThisTask(self, user, testNumber):
    return self.DB.TgiveTaskToClient(user, testNumber)
    # return [true, image-filename1, name2,...]
    # or return [false]


def TreturnTotalledTask(self, user, ret, totalMark):
    """Client has ID'd the pageimage with code=ret, student-number=sid,
    and student-name=sname. Send the information to the database (which
    checks if that number has been used previously). If okay then send
    and ACK, else send an error that the number has been used.
    """
    return self.DB.TtakeTaskFromClient(ret, user, totalMark)


def TdidNotFinish(self, user, testNumber):
    """User didn't finish IDing the image with given code. Tell the
    database to put this back on the todo-pile.
    """
    self.DB.TdidNotFinish(user, testNumber)
    return
