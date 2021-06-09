import hashlib
import os
import uuid


def RgetScannedTests(self):
    return self.DB.RgetScannedTests()


def RgetIncompleteTests(self):
    return self.DB.RgetIncompleteTests()


def RgetMissingHWQ(self):
    return self.DB.RgetMissingHWQ()


def RgetCompleteHW(self):
    return self.DB.RgetCompleteHW()


def RgetUnusedTests(self):
    return self.DB.RgetUnusedTests()


def RgetProgress(self, qu, v):
    return self.DB.RgetProgress(qu, v)


def RgetQuestionUserProgress(self, qu, v):
    return self.DB.RgetQuestionUserProgress(qu, v)


def RgetMarkHistogram(self, qu, v):
    return self.DB.RgetMarkHistogram(qu, v)


def RgetMarked(self, qu, v):
    return self.DB.RgetMarked(qu, v)


def RgetIdentified(self):
    return self.DB.RgetIdentified()


def RgetCompletionStatus(self):
    return self.DB.RgetCompletionStatus()


def RgetOutToDo(self):
    return self.DB.RgetOutToDo()


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
    return sorted(self.DB.getUserList())


def RgetUserDetails(self):
    return self.DB.getUserDetails()
