import hashlib
import os
import uuid


def RgetScannedTests(self):
    return self.DB.RgetScannedTests()


def RgetIncompleteTests(self):
    return self.DB.RgetIncompleteTests()


def RgetUnusedTests(self):
    return self.DB.RgetUnusedTests()


def RgetProgress(self, qu, v):
    return self.DB.RgetProgress(qu, v)


def RgetMarkHistogram(self, qu, v):
    return self.DB.RgetMarkHistogram(qu, v)


def RgetIdentified(self):
    return self.DB.RgetIdentified()


def RgetCompletions(self):
    return self.DB.RgetCompletions()


def RgetStatus(self, testNumber):
    return self.DB.RgetStatus(testNumber)


def RgetSpreadsheet(self):
    return self.DB.RgetSpreadsheet()


def RgetCoverPageInfo(self, testNumber):
    return self.DB.RgetCoverPageInfo(testNumber)


def RgetOriginalFiles(self, testNumber):
    return self.DB.RgetOriginalFiles(testNumber)


def RgetAnnotatedFiles(self, testNumber):
    return self.DB.RgetAnnotatedFiles(testNumber)


def RgetMarkReview(self, filterQ, filterV, filterU):
    return self.DB.RgetMarkReview(filterQ, filterV, filterU)


def RgetIDReview(self):
    return self.DB.RgetIDReview()


def RgetTotReview(self):
    return self.DB.RgetTotReview()


def RgetAnnotatedImage(self, testNumber, questionNumber, version):
    return self.DB.RgetAnnotatedImage(testNumber, questionNumber, version)


def RgetUserList(self):
    return sorted([x for x in self.userList.keys()])


def RgetUserDetails(self):
    rval = {}
    for x in self.userList.keys():
        if self.authority.checkToken(x):
            rval[x] = [True]
        else:
            rval[x] = [False]
        rval[x] += self.DB.RgetUserDetails(x)
    return rval
