import json

class TestSpecification:
    def __init__(self):
        """Set up name, number of tests, length(# pages), number of versions,
        the pages in the ID-group, the page-groups, how to choose each
        page-group, and the marks for each page-group
        """
        self.Name = ""
        self.Tests = 0
        self.Length = 0
        self.Versions = 0
        self.IDGroup = []
        # Note that the ID group is pagegroup[0]
        self.PageGroups = []
        self.FixCycleRandom = []
        self.Marks = []

    def printSpec(self):
        """Print out the specification provided it is valid"""
        if self.checkSpec() == False:
            return

        print("Name of test = ", self.Name)
        print("Number of tests = ", self.Tests)
        print("Number of pages = ", self.Length)
        print("Number of versions = ", self.Versions)
        print("ID pages are =", self.IDGroup)
        print("Number of page groups =", self.getNumberOfGroups())
        # Each pagegroup is either IDpages, fixed (at v1), cycled through
        # versions, or chosen randomly.
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

    def getNumberOfGroups(self):
        # return the number of pagegroups excluding the IDgroup
        return len(self.PageGroups) - 1

    def setIDPages(self, pages):
        # take a list of pages and set it as the idgroup
        self.IDGroup = pages
        self.PageGroups = [pages]
        # not worth any marks
        self.Marks = [0]
        # make sure it is set in the fix-cycle-random list.
        self.FixCycleRandom = ['i']

    def addToSpec(self, t, pages, mark):
        # basic validity checks
        # make sure pages is a list of pages
        # does not check that pages are continguous.
        if type(pages) != list:
            print("Pages must be entered as a list")
            return
        # t = fix-cycle-random  so must be f,c or r.
        if t != 'f' and t != 'c' and t != 'r':
            print("FixCycleRandom must be entered as \'f\', \'c\' or \'r\'")
            return
        # Mark must be non-neg integer
        if type(mark) != int or mark < 0:
            print("Mark must be a non-negative integer")
            return
        # put data into required lists
        self.Marks.append(mark)
        self.FixCycleRandom.append(t)
        self.PageGroups.append(pages)

    def checkSpec(self):
        """Check specification is valid"""
        # Check test name is alphanumeric.
        if not self.Name.isalnum():
            print("Error in spec - name must be non-empty alphanumeric string "
                  "with no spaces {}".format(self.Name))
            return False
        # Check positive number of test, pages and versions
        if self.Tests < 1 or self.Length < 1 or self.Versions < 1:
            print("Error in spec")
            print("Need to produce at least 1 test")
            print("Tests must be at least 1 page")
            print("Tests need at least 1 version")
            return False
        # Check ID group is set
        if not self.IDGroup:
            print("Error in spec - need to set ID pages")
            return False
        # Check length of pagegroups = length of fixcyclerandom = length marks.
        if (len(self.Marks) != len(self.FixCycleRandom)) or \
                (len(self.PageGroups) != len(self.Marks)):
            print("Error in spec - lengths of arrays in spec do not match")
            return False
        # Check each FCR is ifcr.
        for pt in self.FixCycleRandom:
            if pt[0] != 'i' and pt[0] != 'f' and pt[0] != 'c' and pt[0] != 'r':
                print("Error in spec (id/fixed/cycle/random) - ", pt)
                return False
        # Check each pagegroup is sorted.
        for pt in self.PageGroups:
            if pt != sorted(pt):
                print("Error in spec (pages must be in order) - ", pt)
                return False
        # Check each page used exactly once.
        # Add 1 for each time page used.
        used = [0 for x in range(self.Length+1)]
        for pt in self.PageGroups:
            for p in pt:
                used[p] += 1
        # Look at each page
        for k in range(1, len(used)):
            if used[k] != 1:
                print("Error in spec - page {} is used {} times"
                      .format(k, used[k]))
                return False
        # Passed all these checks.
        return True

    def writeSpec(self):
        """Write the specification to file provided it is valid"""
        if not self.checkSpec():
            return
        print("Test Specification is okay, writing to file")
        # We write the test spec as a json file of a dictionary.
        testSpec = {}
        # Now store each part of the spec in this dictionary
        testSpec['Name'] = self.Name
        testSpec['Tests'] = self.Tests
        testSpec['Length'] = self.Length
        testSpec['Versions'] = self.Versions
        testSpec['IDGroup'] = self.IDGroup
        testSpec['PageGroups'] = self.PageGroups
        testSpec['FixCycleRandom'] = self.FixCycleRandom
        testSpec['Marks'] = self.Marks
        # Write it to file.
        tsFH = open("../resources/testSpec.json", 'w')
        tsFH.write(json.dumps(testSpec, indent=4, sort_keys=True))
        tsFH.close()
        # Tell the user
        print("Test Specification written to file")

    def readSpec(self):
        """Read the spec from the json file."""
        print("Loading test spec from file")
        # Read the json into a dictionary
        with open('../resources/testSpec.json') as data_file:
            testSpec = json.load(data_file)
        # Just as when spec is written read things from the dictionary
        self.Name = testSpec['Name']
        self.Tests = testSpec['Tests']
        self.Length = testSpec['Length']
        self.Versions = testSpec['Versions']
        self.IDGroup = testSpec['IDGroup']
        self.PageGroups = testSpec['PageGroups']
        self.FixCycleRandom = testSpec['FixCycleRandom']
        self.Marks = testSpec['Marks']
        # Then check it is valid
        print("Test read - checking is valid")
        if self.checkSpec():
            print("Spec is fine")
        else:
            print("Error in spec")
