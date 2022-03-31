# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2022 Andrew Rechnitzer
# Copyright (C) 2020-2022 Colin B. Macdonald


def RgetScannedTests(self):
    return self.DB.RgetScannedTests()


def RgetIncompleteTests(self):
    return self.DB.RgetIncompleteTests()


def getDanglingPages(self):
    return self.DB.RgetDanglingPages()


def RgetMissingHWQ(self):
    return self.DB.RgetMissingHWQ()


def RgetCompleteHW(self):
    return self.DB.RgetCompleteHW()


def RgetUnusedTests(self):
    return self.DB.RgetUnusedTests()


def RgetProgress(self, spec, qu, v):
    return self.DB.RgetProgress(spec, qu, v)


def RgetQuestionUserProgress(self, qu, v):
    return self.DB.RgetQuestionUserProgress(qu, v)


def RgetMarkHistogram(self, qu, v):
    return self.DB.RgetMarkHistogram(qu, v)


def RgetIdentified(self):
    return self.DB.RgetIdentified()


def RgetNotAutoIdentified(self):
    return self.DB.RgetNotAutoIdentified()


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


def RgetMarkReview(self, *args, **kwargs):
    return self.DB.RgetMarkReview(*args, **kwargs)


def RgetIDReview(self):
    return self.DB.RgetIDReview()


def RgetTotReview(self):
    return self.DB.RgetTotReview()


def RgetUserList(self):
    return sorted(self.DB.getUserList())


def RgetUserDetails(self):
    return self.DB.getUserDetails()


def getFilesInAllTests(self):
    return self.DB.RgetFilesInAllTests()
