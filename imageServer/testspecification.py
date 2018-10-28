import json
import re


class TestSpecification:
    def __init__(self):
        self.Name = ""
        self.Tests = 0
        self.Length = 0
        self.Versions = 0
        self.IDGroup = []
        self.PageGroups = []
        self.FixCycleRandom = []
        self.Marks = []

    def printSpec(self):
        if not self.checkSpec():
            return

        print("Name of test = ", self.Name)
        print("Number of tests = ", self.Tests)
        print("Number of pages = ", self.Length)
        print("Number of versions = ", self.Versions)
        print("ID pages are =", self.IDGroup)
        print("Number of page groups =", self.getNumberOfGroups())

        for k in range(len(self.PageGroups)):
            print("Page group {} is {}".format(k, self.PageGroups[k]), end='')
            if self.FixCycleRandom[k] == 'i':
                print(" is id", end='')
            elif self.FixCycleRandom[k] == 'f':
                print(" is fixed", end='')
            elif self.FixCycleRandom[k] == 'c':
                print(" cycles", end='')
            else:
                print(" is shuffled", end='')
            print(" and is", self.Marks[k], " points")

    def setNumberOfTests(self, n):
        self.Tests = n

    def setNumberOfPages(self, l):
        self.Length = l

    def setNumberOfVersions(self, v):
        self.Versions = v

    def getNumberOfGroups(self):  # This excludes the id pages.
        return len(self.PageGroups)-1

    def setIDPages(self, pages):
        self.IDGroup = pages
        self.PageGroups = [pages]
        self.Marks = [0]
        self.FixCycleRandom = ['i']

    def addToSpec(self, t, pages, mark):
        if type(pages) != list:
            print("Pages must be entered as a list")
            return

        if t != 'f' and t != 'c' and t != 'r':
            print("FixCycleRandom must be entered as \'f\', \'c\' or \'r\'")
            return

        if type(mark) != int or mark < 0:
            print("Mark must be a non-negative integer")
            return

        self.Marks.append(mark)
        self.FixCycleRandom.append(t)
        self.PageGroups.append(pages)

    def checkSpec(self):
        pattern = re.compile("^\w+$")
        if not pattern.match(self.Name):
            print("Error in spec - name must be non-empty alphanumeric string with no spaces {}".format(self.Name))
            quit()
            return

        if self.Tests < 1:
            print("Error in spec - need to produce at least 1 test")
            return
        if self.Length < 1:
            print("Error in spec - tests must be at least 1 page")
            return
        if self.Versions < 1:
            print("Error in spec - need at least 1 version")
            return

        if len(self.IDGroup) == 0:
            print("Error in spec - need to set ID pages")
            return

        if (len(self.Marks) != len(self.FixCycleRandom)) or (len(self.PageGroups) != len(self.Marks)):
            print("ERROR IN SPEC - lengths of arrays in spec do not match")
            return(False)

        for pt in self.FixCycleRandom:
            if pt[0] != 'i' and pt[0] != 'f' and pt[0] != 'c' and pt[0] != 'r':
                print("ERROR IN SPEC (fcr) - ", pt)
                return(False)

        for pt in self.PageGroups:
            if pt != sorted(pt):
                print("ERROR IN SPEC (page order) - ", pt)
                return(False)

        used = [0 for x in range(self.Length+1)]

        for pt in self.PageGroups:
            for p in pt:
                used[p] += 1

        for k in range(1, len(used)):
            if used[k] != 1:
                print("ERROR IN SPEC - page {:d} is used {:d} times".format(k, used[k]))
                return(False)

        return(True)

    def writeSpec(self):
        if not self.checkSpec():
            return
        print("Test Specification is okay, writing to file")

        testSpec = {}
        testSpec['Name'] = self.Name
        testSpec['Tests'] = self.Tests
        testSpec['Length'] = self.Length
        testSpec['Versions'] = self.Versions
        testSpec['IDGroup'] = self.IDGroup
        testSpec['PageGroups'] = self.PageGroups
        testSpec['FixCycleRandom'] = self.FixCycleRandom
        testSpec['Marks'] = self.Marks

        tsFH = open("../resources/testSpec.json", 'w')
        tsFH.write(json.dumps(testSpec, indent=4, sort_keys=True))
        tsFH.close()

        print("Test Specification written to file")

    def readSpec(self):
        print("Loading test spec from file")
        with open('../resources/testSpec.json') as data_file:
            testSpec = json.load(data_file)

        self.Name = testSpec['Name']
        self.Tests = testSpec['Tests']
        self.Length = testSpec['Length']
        self.Versions = testSpec['Versions']
        self.IDGroup = testSpec['IDGroup']
        self.PageGroups = testSpec['PageGroups']
        self.FixCycleRandom = testSpec['FixCycleRandom']
        self.Marks = testSpec['Marks']

        print("Test read - checking is valid")
        if self.checkSpec():
            print("Spec is fine")
        else:
            print("ERROR IN SPEC")
