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


def RgetIdentified(self):
    return self.DB.RgetIdentified()


def RgetCompletions(self):
    return self.DB.RgetCompletions()


def RgetStatus(self, testNumber):
    return self.DB.RgetStatus(testNumber)


def RgetSpreadsheet(self):
    return self.DB.RgetSpreadsheet()


def RgetOriginalFiles(self, testNumber):
    return self.DB.RgetOriginalFiles(testNumber)
