from peewee import *
from datetime import datetime, timedelta

# import logging
# logger = logging.getLogger("peewee")
# logger.addHandler(logging.StreamHandler())
# logger.setLevel(logging.DEBUG)


plomdb = SqliteDatabase("../resources/plom.db")

# the test contains groups
# test bools something like
# produced = we've built the PDF
# used = we've scanned at least one page
# scanned = we've fed it to students, scanned it into system.
# identified = ID-ing is done
# marked = marking is done
# finished = we've rebuilt the PDF at the end with coverpages etc etc


class Test(Model):
    testNumber = IntegerField(primary_key=True, unique=True)
    # some state bools
    produced = BooleanField(default=False)
    used = BooleanField(default=False)
    scanned = BooleanField(default=False)
    identified = BooleanField(default=False)
    marked = BooleanField(default=False)
    finished = BooleanField(default=False)
    totalled = BooleanField(default=False)

    class Meta:
        database = plomdb


# group knows its test
# group status will evolve something like... [todo, outwithclient, done]
class Group(Model):
    test = ForeignKeyField(Test, backref="groups")
    gid = CharField(unique=True)  # must be unique
    groupType = CharField()  # to distinguish between ID, DNM, and Mark groups
    # flags
    scanned = BooleanField(default=False)

    class Meta:
        database = plomdb


# Data for id-group
class IDData(Model):
    test = ForeignKeyField(Test, backref="iddata")
    group = ForeignKeyField(Group, backref="iddata")
    status = CharField(default="")
    studentID = CharField(unique=True, null=True)
    studentName = CharField(null=True)
    username = CharField(default="")
    time = DateTimeField(null=True)
    # flags
    identified = BooleanField(default=False)

    class Meta:
        database = plomdb


# Data for question-groups
class QuestionData(Model):
    test = ForeignKeyField(Test, backref="questiondata")
    group = ForeignKeyField(Group, backref="questiondata")
    status = CharField(default="")
    questionNumber = IntegerField(null=False)
    version = IntegerField(null=False)
    annotatedFile = CharField(null=True)
    m5dsum = CharField(null=True)
    plomFile = CharField(null=True)
    commentFile = CharField(null=True)
    mark = IntegerField(null=True)
    markingTime = IntegerField(null=True)
    tags = CharField(default="")
    username = CharField(default="")
    time = DateTimeField(null=True)
    # flags
    marked = BooleanField(default=False)

    class Meta:
        database = plomdb


# Data for totalling the marks
class SumData(Model):
    test = ForeignKeyField(Test, backref="sumdata")
    status = CharField(default="")
    sumMark = IntegerField(null=True)
    username = CharField(default="")
    time = DateTimeField(null=True)
    # flags
    summed = BooleanField(default=False)

    class Meta:
        database = plomdb


# Page knows its group and its test
class Page(Model):
    test = ForeignKeyField(Test, backref="pages")
    group = ForeignKeyField(Group, backref="pages")  # note - not the GID
    pageNumber = IntegerField(null=False)
    pid = CharField(unique=True)  # to ensure uniqueness
    version = IntegerField(default=1)
    originalName = CharField(null=True)
    fileName = CharField(null=True)
    md5sum = CharField(null=True)  # to check for duplications
    # flags
    scanned = BooleanField(default=False)

    class Meta:
        database = plomdb


# Colliding pages should be attached to the page their are duplicating
# When collision status resolved we can move them about.
class CollidingPage(Model):
    page = ForeignKeyField(Page, backref="collisions")
    originalName = CharField(null=True)
    fileName = CharField(null=True)
    md5sum = CharField()

    class Meta:
        database = plomdb


# Unknown pages are basically just the file
class UnknownPage(Model):
    originalName = CharField(null=True)
    fileName = CharField(null=True)
    md5sum = CharField()

    class Meta:
        database = plomdb


# Discarded pages are basically just the file and a reason
# reason could be "garbage", "duplicate of tpv-code", ...?
class DiscardedPage(Model):
    originalName = CharField(null=True)
    fileName = CharField(null=True)
    md5sum = CharField()
    reason = CharField(null=True)
    tpv = CharField(null=True)  # if the discard is a duplicate of a given tpv

    class Meta:
        database = plomdb


class PlomDB:
    def __init__(self):
        with plomdb:
            plomdb.create_tables(
                [
                    Test,
                    Group,
                    IDData,
                    QuestionData,
                    SumData,
                    Page,
                    UnknownPage,
                    CollidingPage,
                    DiscardedPage,
                ]
            )

    def createTest(self, t):
        try:
            tref = Test.create(testNumber=t)  # must be unique
            # also create the sum-mark objects
            sref = SumData.create(test=tref)
        except IntegrityError as e:
            print("Test {} error - {}".format(t, e))
            return False
        return True

    def addPages(self, tref, gref, t, pages, v):
        flag = True
        with plomdb.atomic():
            for p in pages:
                try:
                    Page.create(
                        test=tref,
                        group=gref,
                        gid=gref.gid,
                        pageNumber=p,
                        version=v,
                        pid="t{}p{}".format(t, p),
                        originalName="",
                        fileName="",
                    )
                except IntegrityError as e:
                    print("Page {} for test {} error - {}".format(p, t, e))
                    print(e)
                    flag = False
        return flag

    def createIDGroup(self, t, pages):
        tref = Test.get_or_none(testNumber=t)
        if tref is None:
            print("No test with number {}".format(t))
            return False

        gid = "i{}".format(str(t).zfill(4))
        try:
            gref = Group.create(test=tref, gid=gid, groupType="i")  # must be unique
        except IntegrityError as e:
            print("Group {} of Test {} error - {}".format(gid, t, e))
            return False
        try:
            iref = IDData.create(test=tref, group=gref)
        except IntegrityError as e:
            print(e)
            print("IDData {} of group {} error - {}.".format(qref, gref, e))
            return False
        return self.addPages(tref, gref, t, pages, 1)

    def createDNMGroup(self, t, pages):
        tref = Test.get_or_none(testNumber=t)
        if tref is None:
            print("No test with number {}".format(t))
            return False

        gid = "d{}".format(str(t).zfill(4))
        # make the dnmgroup
        try:
            # A DNM group may have 0 pages, in that case mark it as scanned and set status = "complete"
            sc = True if len(pages) == 0 else False
            gref = Group.create(test=tref, gid=gid, groupType="d", scanned=sc)

        except IntegrityError as e:
            print("Group {} of Test {} error - {}".format(gid, t, e))
            return False
        return self.addPages(tref, gref, t, pages, 1)

    def createQGroup(self, t, g, v, pages):
        tref = Test.get_or_none(testNumber=t)
        if tref is None:
            print("No test with number {}".format(t))
            return False

        gid = "m{}g{}".format(str(t).zfill(4), g)
        # make the mgroup
        try:
            gref = Group.create(test=tref, gid=gid, groupType="m", version=v)
        except IntegrityError as e:
            print("Question {} of Test {} error - {}".format(gid, t, e))
            return False
        try:
            qref = QuestionData.create(
                test=tref, group=gref, questionNumber=g, version=v
            )
        except IntegrityError as e:
            print(e)
            print("QuestionData {} of question {} error - {}.".format(qref, gid, e))
            return False
        return self.addPages(tref, gref, t, pages, v)

    def printGroups(self, t):
        tref = Test.get_or_none(testNumber=t)
        if tref is None:
            return
        for x in tref.groups:
            print(x.gid, x.groupType)
            if x.groupType == "i":
                idata = x.iddata[0]
                print("\t", idata.studentID, idata.studentName)
            elif x.groupType == "m":
                qdata = x.questiondata[0]
                print(
                    "\t",
                    qdata.questionNumber,
                    qdata.version,
                    qdata.status,
                    qdata.mark,
                    qdata.annotatedFile,
                )
            for p in x.pages.order_by(Page.pageNumber):
                print("\t", [p.pageNumber, p.version])

    def printPagesByTest(self, t):
        tref = Test.get_or_none(testNumber=t)
        if tref is None:
            return
        for p in tref.pages.order_by(Page.pageNumber):
            print(p.pageNumber, p.version, p.group.gid)

    def getPageVersions(self, t):
        tref = Test.get_or_none(testNumber=t)
        if tref is None:
            return {}
        else:
            pvDict = {p.pageNumber: p.version for p in tref.pages}
            return pvDict

    def produceTest(self, t):
        # After creating the test (003 script) we'll turn the spec'd papers into PDFs
        # we'll refer to those as "produced"
        tref = Test.get_or_none(testNumber=t)
        if tref is None:
            return
        else:
            # TODO - work out how to make this more efficient? Multiple updates in one op?
            with plomdb.atomic():
                for p in tref.pages:
                    p.save()
                for g in tref.groups:
                    g.save()
                tref.produced = True
                tref.save()

    def identifyTest(self, t, sid, sname):
        tref = Test.get_or_none(testNumber=t)
        if tref is None:
            return
        iref = IDData.get_or_none(test=tref)
        if iref is None:
            return
        with plomdb.atomic():
            iref.status = "done"
            iref.studentID = sid
            iref.studentName = sname
            iref.identified = True
            iref.username = "automatic"
            iref.time = datetime.now()
            iref.save()
            tref.identified = True
            tref.save()

    def checkTestAllUploaded(self, gref):
        tref = gref.test
        sflag = True
        for g in tref.groups:
            if g.scanned == False:
                # TODO - deal with empty DO NOT MARK groups correctly
                sflag = False
                print("\t Group {} not scanned".format(g.gid))
                break
        with plomdb.atomic():
            if sflag:
                tref.scanned = True
                print("Test {} is all scanned".format(tref.testNumber))
                # set the status of the sumdata
                sdref = tref.sumdata[0]
                sdref.status = "todo"
                sdref.save()
            else:
                tref.scanned = False
            tref.save()

    def setGroupReady(self, gref):
        print("All of group {} is scanned".format(gref.gid))
        if gref.groupType == "i":
            iref = gref.iddata[0]
            # check if group already identified - can happen if printed tests with names
            if iref.status == "done":
                print("Group {} is already identified.".format(gref.gid))
            else:
                iref.status = "todo"
                print("Group {} is ready to be identified.".format(gref.gid))
            iref.save()
        elif gref.groupType == "d":
            # we don't do anything with these groups
            print(
                "Group {} is DoNotMark - all scanned, nothing to be done.".format(
                    gref.gid
                )
            )
        elif gref.groupType == "m":
            print("Group {} is ready to be marked.".format(gref.gid))
            qref = gref.questiondata[0]
            qref.status = "todo"
            qref.save()

    def checkGroupAllUploaded(self, pref):
        gref = pref.group
        sflag = True
        for p in gref.pages:
            if p.scanned == False:
                sflag = False
                break
        with plomdb.atomic():
            if sflag:
                gref.scanned = True
                self.setGroupReady(gref)
            else:
                gref.scanned = False
            gref.save()
        if sflag:
            self.checkTestAllUploaded(gref)

    def replaceMissingPage(self, t, p, v, oname, nname, md5):
        tref = Test.get_or_none(testNumber=t)
        if tref is None:
            return [False, "testError", "Cannot find test {}".format(t)]
        pref = Page.get_or_none(test=tref, pageNumber=p, version=v)
        if pref is None:
            return [
                False,
                "pageError",
                "Cannot find page {} for test {}".format(p, t),
            ]
        if pref.scanned:
            return [
                False,
                "pageScanned",
                "Page is already scanned",
            ]
        else:  # this is a new page.
            with plomdb.atomic():
                pref.originalName = oname
                pref.fileName = nname
                pref.md5sum = md5
                pref.scanned = True
                pref.save()
                tref.used = True
                tref.save()
            self.checkGroupAllUploaded(pref)
            return [True, "success", "Page saved as {}".format(pref.pid)]

    def fileOfScannedPage(self, t, p, v):
        tref = Test.get_or_none(testNumber=t)
        if tref is None:
            return None
        pref = Page.get_or_none(test=tref, pageNumber=p, version=v)
        if pref is None:
            return None
        return pref.fileName

    def createDiscardedPage(self, oname, fname, md5, r, tpv):
        DiscardedPage.create(
            originalName=oname, fileName=fname, md5sum=md5, reason=r, tpv=tpv
        )

    def removeScannedPage(self, fname, nname):
        pref = Page.get_or_none(fileName=fname)
        if pref is None:
            return False
        with plomdb.atomic():
            pref.scanned = False
            pref.originalName = None
            pref.fileName = None
            pref.md5sum = None
            pref.scanned = False
            pref.save()

        tref = pref.test
        gref = pref.group
        # now update the group
        if gref.groupType == "d":
            rlist = self.invalidateDNMGroup(tref, gref)
        elif gref.groupType == "i":
            rlist = self.invalidateIDGroup(tref, gref)
        elif gref.groupType == "m":
            rlist = self.invalidateQGroup(tref, gref)
        return [True, rlist]

    def invalidateDNMGroup(self, gref):
        with plomdb.atomic():
            tref.scanned = False
            tref.finished = False
            tref.save()
            gref.scanned = False
            gref.save()
        return []

    def invalidateIDGroup(self, tref, gref):
        iref = gref.iddata[0]
        with plomdb.atomic():
            tref.scanned = False
            tref.identified = False
            tref.finished = False
            tref.save()
            gref.scanned = False
            gref.save()
            iref.status = ""
            iref.username = ""
            iref.time = datetime.now()
            iref.studentID = None
            iref.studentName = None
            iref.save()
        return []

    def invalidateQGroup(self, tref, gref):
        qref = gref.questiondata[0]
        sref = tref.sumdata[0]
        rval = []
        with plomdb.atomic():
            # update the test
            tref.scanned = False
            tref.marked = False
            tref.totalled = False
            tref.finished = False
            tref.save()
            # update the group
            gref.scanned = False
            gref.save()
            # update the sumdata
            sref.status = ""
            sref.sumMark = None
            sref.username = ""
            sref.time = datetime.now()
            sref.summed = False
            sref.save()
            # update the questionData - first get filenames if they exist
            if qref.marked:
                rval = [
                    qref.annotatedFile,
                    qref.plomFile,
                    qref.commentFile,
                ]
            qref.marked = False
            qref.status = ""
            qref.annotatedFile = None
            qref.plomFile = None
            qref.commentFile = None
            qref.mark = None
            qref.markingTime = None
            qref.tags = ""
            qref.username = ""
            qref.time = datetime.now()
            qref.save
        return rval

    def uploadKnownPage(self, t, p, v, oname, nname, md5):
        # return value is either [True, <success message>] or
        # [False, stuff] - but need to distinguish between "discard this image" and "you should perhaps keep this image"
        # So return either [False, "discard", discard message]
        # or [False, "keep", keep this image message]
        tref = Test.get_or_none(testNumber=t)
        if tref is None:
            return [False, "testError", "Cannot find test {}".format(t)]
        pref = Page.get_or_none(test=tref, pageNumber=p, version=v)
        if pref is None:
            return [
                False,
                "pageError",
                "Cannot find page,version {} for test {}".format([p, v], t),
            ]
        if pref.scanned:
            # have already loaded an image for this page - so this is actually a duplicate
            print("This appears to be a duplicate. Checking md5sums")
            if md5 == pref.md5sum:
                # Exact duplicate - md5sum of this image is sames as the one already in database
                return [
                    False,
                    "duplicate",
                    "Exact duplicate of page already in database",
                ]
            # Deal with duplicate pages separately. return to sender (as it were)
            # At present just return "collision" - in future we need to check if this is a new collision
            # or if it is the duplicate of an existing collision.
            return [False, "collision", ["{}".format(pref.originalName), t, p, v]]
        else:  # this is a new page.
            with plomdb.atomic():
                pref.originalName = oname
                pref.fileName = nname
                pref.md5sum = md5
                pref.scanned = True
                pref.save()
                tref.used = True
                tref.save()
            self.checkGroupAllUploaded(pref)
            return [True, "success", "Page saved as {}".format(pref.pid)]

    def uploadUnknownPage(self, oname, nname, md5):
        # return value is either [True, <success message>] or
        # [False, <duplicate message>]
        # check if md5 is already in Unknown pages
        uref = UnknownPage.get_or_none(md5sum=md5)
        if uref is not None:
            return [
                False,
                "duplicate",
                "Exact duplicate of page already in database",
            ]
        with plomdb.atomic():
            uref = UnknownPage.create(originalName=oname, fileName=nname, md5sum=md5)
            uref.save()
        return [True, "success", "Page saved in UnknownPage list"]

    def uploadCollidingPage(self, t, p, v, oname, nname, md5):
        tref = Test.get_or_none(testNumber=t)
        if tref is None:
            return [False, "testError", "Cannot find test {}".format(t)]
        pref = Page.get_or_none(test=tref, pageNumber=p, version=v)
        if pref is None:
            return [
                False,
                "pageError",
                "Cannot find page,version {} for test {}".format([p, v], t),
            ]
        if not pref.scanned:
            return [
                False,
                "original",
                "This is not a collision - this page was not scanned previously",
            ]
        # check this against other collisions
        for cp in pref.collisions:
            if md5 == cp.md5sum:
                # Exact duplicate - md5sum of this image is sames as the one already in database
                return [
                    False,
                    "duplicate",
                    "Exact duplicate of page already in database",
                ]
        with plomdb.atomic():
            cref = CollidingPage.create(
                originalName=oname, fileName=nname, md5sum=md5, page=pref
            )
            cref.save()
        return [
            True,
            "success",
            "Colliding page saved, attached to {}".format(pref.pid),
        ]

    # def checkTestPageUnscanned(self, testNumber, pageNumber, version):
    #     # returns True only if we can find test+page and page is unscanned
    #
    #     tref = Test.get_or_none(Test.testNumber == testNumber)
    #     if tref is None:
    #         return [False, "Test not found"]
    #     pref = Page.get_or_none(
    #         Page.test == tref, Page.pageNumber == pageNumber, Page.version == version
    #     )
    #     if pref is None:
    #         return [False, "Page not found"]
    #     if pref.scanned == False:
    #         return [True, "Missing page replaced"]
    #     else:
    #         return [False, "Already scanned"]

    def getUnknownPageNames(self):
        rval = []
        for uref in UnknownPage.select():
            rval.append(uref.fileName)
        return rval

    def getDiscardNames(self):
        rval = []
        for dref in DiscardedPage.select():
            rval.append(dref.fileName)
        return rval

    def getCollidingPageNames(self):
        rval = {}
        for cref in CollidingPage.select():
            rval[cref.fileName] = [
                cref.page.test.testNumber,
                cref.page.pageNumber,
                cref.page.version,
            ]
        return rval

    def getPageImage(self, testNumber, pageNumber, version):
        tref = Test.get_or_none(Test.testNumber == testNumber)
        if tref is None:
            return [False]
        pref = Page.get_or_none(
            Page.test == tref, Page.pageNumber == pageNumber, Page.version == version
        )
        if pref is None:
            return [False]
        else:
            return [True, pref.fileName]

    def getUnknownImage(self, fname):
        uref = UnknownPage.get_or_none(UnknownPage.fileName == fname)
        if uref is None:
            return [False]
        else:
            return [True, uref.fileName]

    def getDiscardImage(self, fname):
        dref = DiscardedPage.get_or_none(DiscardedPage.fileName == fname)
        if dref is None:
            return [False]
        else:
            return [True, dref.fileName]

    def getCollidingImage(self, fname):
        cref = CollidingPage.get_or_none(CollidingPage.fileName == fname)
        if cref is None:
            return [False]
        else:
            return [True, cref.fileName]

    def getQuestionImages(self, testNumber, questionNumber):
        tref = Test.get_or_none(Test.testNumber == testNumber)
        if tref is None:
            return [False]
        qref = QuestionData.get_or_none(
            QuestionData.test == tref, QuestionData.questionNumber == questionNumber
        )
        if qref is None:
            return [False]
        rval = [True]
        for p in qref.group.pages.order_by(Page.pageNumber):
            rval.append(p.fileName)
        return rval

    def getTestImages(self, testNumber):
        tref = Test.get_or_none(Test.testNumber == testNumber)
        if tref is None:
            return [False]
        rval = [True]
        for p in tref.pages.order_by(Page.pageNumber):
            rval.append(p.fileName)
        return rval

    def checkPage(self, testNumber, pageNumber):
        tref = Test.get_or_none(Test.testNumber == testNumber)
        if tref is None:
            return [False]
        pref = Page.get_or_none(Page.test == tref, Page.pageNumber == pageNumber)
        if pref is None:
            return [False]
        if pref.scanned:
            return [True, pref.version, pref.fileName]
        else:
            return [True, pref.version]

    def checkUnknownImage(self, fname):
        uref = UnknownPage.get_or_none(UnknownPage.fileName == fname)
        if uref is None:
            return None
        return [uref.fileName, uref.originalName, uref.md5sum]

    def checkCollidingImage(self, fname):
        cref = CollidingPage.get_or_none(CollidingPage.fileName == fname)
        if cref is None:
            return None
        return [cref.fileName, cref.originalName, cref.md5sum]

    def removeUnknownImage(self, fname, nname):
        uref = UnknownPage.get_or_none(UnknownPage.fileName == fname)
        if uref is None:
            return False
        with plomdb.atomic():
            DiscardedPage.create(
                fileName=nname, originalName=uref.originalName, md5sum=uref.md5sum
            )
            uref.delete_instance()
        return True

    def removeCollidingImage(self, fname, nname):
        cref = CollidingPage.get_or_none(fileName=fname)
        if cref is None:
            return False
        with plomdb.atomic():
            DiscardedPage.create(
                fileName=nname, originalName=cref.originalName, md5sum=cref.md5sum
            )
            cref.delete_instance()
        return True

    def moveUnknownToPage(self, fname, nname, testNumber, pageNumber):
        uref = UnknownPage.get_or_none(UnknownPage.fileName == fname)
        if uref is None:
            print("No uref")
            return [False]
        tref = Test.get_or_none(Test.testNumber == testNumber)
        if tref is None:
            print("No tref")
            return [False]
        pref = Page.get_or_none(Page.test == tref, Page.pageNumber == pageNumber)
        if pref is None:
            print("No pref")
            return [False]
        with plomdb.atomic():
            pref.fileName = nname
            pref.md5sum = uref.md5sum
            pref.originalName = uref.originalName
            pref.scanned = True
            pref.save()
            uref.delete_instance()
        self.checkGroupAllUploaded(pref)
        return [True]

    def moveUnknownToCollision(self, fname, nname, testNumber, pageNumber):
        uref = UnknownPage.get_or_none(UnknownPage.fileName == fname)
        if uref is None:
            return [False]
        tref = Test.get_or_none(Test.testNumber == testNumber)
        if tref is None:
            return [False]
        pref = Page.get_or_none(Page.test == tref, Page.pageNumber == pageNumber)
        if pref is None:
            return [False]
        with plomdb.atomic():
            CollidingPage.create(
                page=pref,
                originalName=uref.originalName,
                fileName=nname,
                md5sum=uref.md5sum,
            )
            uref.delete_instance()
            return [True]

    def moveCollidingToPage(self, fname, nname, testNumber, pageNumber, version):
        cref = CollidingPage.get_or_none(CollidingPage.fileName == fname)
        if cref is None:
            return [False]
        tref = Test.get_or_none(Test.testNumber == testNumber)
        if tref is None:
            return [False]
        pref = Page.get_or_none(
            Page.test == tref, Page.pageNumber == pageNumber, Page.version == version
        )
        if pref is None:
            return [False]
        with plomdb.atomic():
            pref.fileName = nname
            pref.md5sum = cref.md5sum
            pref.originalName = cref.originalName
            pref.scanned = True
            pref.save()
            cref.delete_instance()
        self.checkGroupAllUploaded(pref)
        return [True]

    def moveExtraToPage(self, fname, nname, testNumber, questionNumber):
        uref = UnknownPage.get_or_none(UnknownPage.fileName == fname)
        if uref is None:
            return [False]
        tref = Test.get_or_none(Test.testNumber == testNumber)
        if tref is None:
            return [False]
        # find the group to which the new page should belong
        qref = QuestionData.get_or_none(test=tref, questionNumber=questionNumber)
        if qref is None:
            return [False]
        version = qref.version
        # get the last page in the test.
        pref = (
            Page.select()
            .where(Page.test == tref)
            .order_by(Page.pageNumber.desc())
            .get()
        )
        # extra pages start with page-number 1001
        nextPageNumber = max(pref.pageNumber + 1, 1001)
        with plomdb.atomic():
            npref = Page.create(
                test=tref,
                group=qref.group,
                gid=qref.group.gid,
                pageNumber=nextPageNumber,
                version=version,
                pid="t{}p{}".format(testNumber, nextPageNumber),
                originalName=uref.originalName,
                fileName=nname,  # since the file is moved
                md5sum=uref.md5sum,
                scanned=True,
            )
            uref.delete_instance()
        ## Now invalidate any work on the associated group
        # now update the group
        return [True, self.invalidateQGroup(tref, qref.group)]

    def moveDiscardToUnknown(self, fname, nname):
        dref = DiscardedPage.get_or_none(fileName=fname)
        if dref is None:
            return [False]
        with plomdb.atomic():
            uref = UnknownPage.create(
                originalName=dref.originalName, fileName=nname, md5sum=dref.md5sum
            )
            uref.save()
            dref.delete_instance()
        return [True]

    # ------------------
    # Reporting functions

    def RgetScannedTests(self):
        rval = {}
        for tref in Test.select().where(Test.scanned == True):
            pScanned = []
            for p in tref.pages:
                if p.scanned == True:
                    pScanned.append([p.pageNumber, p.version])
            rval[tref.testNumber] = pScanned
        return rval

    def RgetIncompleteTests(self):
        rval = {}
        for tref in Test.select().where(Test.scanned == False, Test.used == True):
            pMissing = []
            for p in tref.pages:
                if p.scanned == False:
                    pMissing.append([p.pageNumber, p.version])
            rval[tref.testNumber] = pMissing
        return rval

    def RgetUnusedTests(self):
        rval = []
        for tref in Test.select().where(Test.used == False):
            rval.append(tref.testNumber)
        return rval

    def RgetIdentified(self):
        rval = {}
        for iref in IDData.select().where(IDData.identified == True):
            rval[iref.test.testNumber] = iref.studentID
        return rval

    def RgetProgress(self, q, v):
        # return [numberScanned, numberMarked, numberRecent, avgMark, avgTimetaken]
        oneHour = timedelta(hours=1)
        NScanned = 0
        NMarked = 0
        NRecent = 0
        SMark = 0
        SMTime = 0
        for x in (
            QuestionData.select()
            .join(Group)
            .where(
                QuestionData.questionNumber == q,
                QuestionData.version == v,
                Group.scanned == True,
            )
        ):
            NScanned += 1
            if x.marked == True:
                NMarked += 1
                SMark += x.mark
                SMTime += x.markingTime
                if datetime.now() - x.time < oneHour:
                    NRecent += 1

        if NMarked == 0:
            return {
                "NScanned": NScanned,
                "NMarked": NMarked,
                "NRecent": NRecent,
                "avgMark": None,
                "avgMTime": None,
            }
        else:
            return {
                "NScanned": NScanned,
                "NMarked": NMarked,
                "NRecent": NRecent,
                "avgMark": SMark / NMarked,
                "avgMTime": SMTime / NMarked,
            }

    def RgetMarkHistogram(self, q, v):
        rhist = {}
        # defaultdict(lambda: defaultdict(int))
        for x in (
            QuestionData.select()
            .join(Group)
            .where(
                QuestionData.questionNumber == q,
                QuestionData.version == v,
                QuestionData.marked == True,
                Group.scanned == True,
            )
        ):
            # make sure username and mark both in histogram
            if x.username not in rhist:
                rhist[x.username] = {}
            if x.mark not in rhist[x.username]:
                rhist[x.username][x.mark] = 0
            rhist[x.username][x.mark] += 1
        return rhist

    def RgetCompletions(self):
        rval = {}
        for tref in Test.select().where(Test.scanned == True):
            numMarked = (
                QuestionData.select()
                .where(QuestionData.test == tref, QuestionData.marked == True)
                .count()
            )
            rval[tref.testNumber] = [tref.identified, tref.totalled, numMarked]
        return rval

    def RgetStatus(self, testNumber):
        tref = Test.get_or_none(Test.testNumber == testNumber)
        if tref is None:
            return [False]
        rval = {
            "number": tref.testNumber,
            "identified": tref.identified,
            "marked": tref.marked,
            "totalled": tref.totalled,
        }
        if tref.identified:
            iref = tref.iddata[0]
            rval["sid"] = iref.studentID
            rval["sname"] = iref.studentName
            rval["iwho"] = iref.username
        if tref.totalled:
            sref = tref.sumdata[0]
            rval["total"] = sref.sumMark
            rval["twho"] = sref.username
        for qref in tref.questiondata:
            rval[qref.questionNumber] = {
                "marked": qref.marked,
                "mark": qref.mark,
                "version": qref.version,
                "who": qref.username,
            }

        return [True, rval]

    def RgetSpreadsheet(self):
        rval = {}
        for tref in Test.select().where(Test.scanned == True):
            thisTest = {
                "identified": tref.identified,
                "marked": tref.marked,
                "totalled": tref.totalled,
                "finished": tref.finished,
                "sid": "",
                "sname": "",
            }
            iref = tref.iddata[0]
            if tref.identified:
                thisTest["sid"] = iref.studentID
                thisTest["sname"] = iref.studentName
            for qref in tref.questiondata:
                thisTest["q{}v".format(qref.questionNumber)] = qref.version
                thisTest["q{}m".format(qref.questionNumber)] = ""
                if qref.marked:
                    thisTest["q{}m".format(qref.questionNumber)] = qref.mark
            rval[tref.testNumber] = thisTest
        return rval

    def RgetOriginalFiles(self, testNumber):
        rval = []
        tref = Test.get_or_none(testNumber=testNumber)
        if tref is None:
            return []
        for p in tref.pages.order_by(Page.pageNumber):
            rval.append(p.fileName)
        return rval

    def RgetCoverPageInfo(self, testNumber):
        tref = Test.get_or_none(testNumber=testNumber)
        if tref is None:
            return []
        # [ID, Name]
        iref = tref.iddata[0]
        rval = [[iref.studentID, iref.studentName]]
        # then [q, v, mark]
        for g in tref.questiondata.order_by(QuestionData.questionNumber):
            rval.append([g.questionNumber, g.version, g.mark])
        return rval

    def RgetAnnotatedFiles(self, testNumber):
        rval = []
        tref = Test.get_or_none(testNumber=testNumber)
        if tref is None:
            return []
        # append ID-pages, then DNM-pages, then QuestionGroups
        gref = Group.get_or_none(Group.test == tref, Group.groupType == "i")
        for p in gref.pages.order_by(Page.pageNumber):
            rval.append(p.fileName)
        # append DNM pages
        gref = Group.get_or_none(Group.test == tref, Group.groupType == "d")
        for p in gref.pages.order_by(Page.pageNumber):
            rval.append(p.fileName)
        # append questiongroups
        for g in tref.questiondata.order_by(QuestionData.questionNumber):
            rval.append(g.annotatedFile)
        return rval

    # ------------------
    # For user login - we reset all their stuff that is out

    def resetUsersToDo(self, username):
        with plomdb.atomic():
            query = IDData.select().where(
                IDData.username == username, IDData.status == "out"
            )
            for x in query:
                x.status = "todo"
                x.username = ""
                x.time = datetime.now()
                x.save()
        with plomdb.atomic():
            query = QuestionData.select().where(
                QuestionData.username == username, QuestionData.status == "out",
            )
            for x in query:
                x.status = "todo"
                x.username = ""
                x.markingTime = 0
                x.time = datetime.now()
                x.save()
        with plomdb.atomic():
            query = SumData.select().where(
                SumData.username == username, SumData.status == "out"
            )
            for x in query:
                x.status = "todo"
                x.username = ""
                x.time = datetime.now()
                x.save()

    # ------------------
    # Identifier stuff
    # The ID-able tasks have grouptype ="i", group.scanned=True,
    # The todo id-tasks are iddata.status="todo"
    # the done id-tasks have iddata.status="done"

    def IDcountAll(self):
        """Count all the records"""
        try:
            return (
                Group.select()
                .where(Group.groupType == "i", Group.scanned == True,)
                .count()
            )
        except Group.DoesNotExist:
            return 0

    def IDcountIdentified(self):
        """Count all the ID'd records"""
        try:
            return (
                IDData.select()
                .join(Group)
                .where(Group.scanned == True, IDData.identified == True,)
                .count()
            )
        except IDData.DoesNotExist:
            return 0

    def IDgetNextTask(self):
        """Find unid'd test and send testNumber to client"""
        with plomdb.atomic():
            try:
                x = (
                    IDData.select()
                    .join(Group)
                    .where(IDData.status == "todo", Group.scanned == True,)
                    .get()
                )
            except IDData.DoesNotExist:
                print("Nothing left on to-do pile")
                return None

            print("Next ID task = {}".format(x.test.testNumber))
            return x.test.testNumber

    def IDgiveTaskToClient(self, username, testNumber):
        try:
            with plomdb.atomic():
                tref = Test.get_or_none(Test.testNumber == testNumber)
                if tref.scanned == False:
                    return [False]
                iref = tref.iddata[0]
                if iref.username != "" and iref.username != username:
                    # has been claimed by someone else.
                    return [False]
                # update status, Student-number, name, id-time.
                iref.status = "out"
                iref.username = username
                iref.time = datetime.now()
                iref.save()
                # return [true, page1, page2, etc]
                gref = iref.group
                rval = [True]
                for p in gref.pages.order_by(Page.pageNumber):
                    rval.append(p.fileName)
                print("Giving ID task {} to user {}".format(testNumber, username))
                return rval

        except Test.DoesNotExist:
            print("That test number {} not known".format(testNumber))
            return False

    def IDgetDoneTasks(self, username):
        """When a id-client logs on they request a list of papers they have already IDd.
        Send back the list."""
        query = IDData.select().where(
            IDData.username == username, IDData.status == "done"
        )
        idList = []
        for x in query:
            idList.append([x.test.testNumber, x.status, x.studentID, x.studentName])
        return idList

    def IDgetImage(self, username, t):
        tref = Test.get_or_none(Test.testNumber == t)
        if tref.scanned == False:
            return [False]
        iref = tref.iddata[0]
        # check if task given to user
        if username not in [iref.username, "manager"]:
            return [False]
        gref = iref.group
        rval = [True]
        for p in gref.pages.order_by(Page.pageNumber):
            rval.append(p.fileName)
        print("Sending IDpages of test {} to user {}".format(t, username))
        return rval

    def IDdidNotFinish(self, username, testNumber):
        """When user logs off, any images they have still out should be put
        back on todo pile
        """
        # Log user returning given tgv.
        print("User {} did not ID task {}".format(username, testNumber))
        try:
            with plomdb.atomic():
                tref = Test.get_or_none(Test.testNumber == testNumber)
                if tref.scanned == False:
                    return
                iref = tref.iddata[0]
                if iref.username != username or iref.status != "out":
                    # has been claimed by someone else.
                    return
                # update status, Student-number, name, id-time.
                iref.status = "todo"
                iref.username = ""
                iref.time = datetime.now()
                iref.identified = False
                iref.save()
                tref.identified = False
                tref.save()

        except Test.DoesNotExist:
            print("That test number {} not known".format(testNumber))
            return False

    def IDtakeTaskFromClient(self, testNumber, username, sid, sname):
        """Get ID'dimage back from client - update record in database."""
        print(
            "User {} returning ID-task {} with {} {}".format(
                username, testNumber, sid, sname
            )
        )
        try:
            with plomdb.atomic():
                tref = Test.get_or_none(Test.testNumber == testNumber)
                if tref.scanned == False:
                    return [False, False]
                iref = tref.iddata[0]
                if iref.username != username:
                    # that belongs to someone else - this is a serious error
                    return [False, False]
                # update status, Student-number, name, id-time.
                iref.status = "done"
                iref.studentID = sid
                iref.studentName = sname
                iref.identified = True
                iref.time = datetime.now()
                iref.save()
                tref.identified = True
                tref.save()
                return [True]
        except IDData.DoesNotExist:
            print("That test number {} not known".format(testNumber))
            return [False, False]
        except IntegrityError:
            print("Student number {} already entered".format(sid))
            return [False, True]

    def IDgetRandomImage(self):
        # TODO - make random image rather than 1st
        gref = Group.get_or_none(Group.groupType == "i", Group.scanned == True)
        if gref is None:
            return [False]
        rval = [True]
        for p in gref.pages.order_by(Page.pageNumber):
            rval.append(p.fileName)
        return rval

    # ------------------
    # Marker stuff

    def McountAll(self, q, v):
        """Count all the records"""
        try:
            return (
                QuestionData.select()
                .join(Group)
                .where(
                    QuestionData.questionNumber == q,
                    QuestionData.version == v,
                    Group.scanned == True,
                )
                .count()
            )
        except QuestionData.DoesNotExist:
            return 0

    def McountMarked(self, q, v):
        """Count all the Marked records"""
        try:
            return (
                QuestionData.select()
                .join(Group)
                .where(
                    QuestionData.questionNumber == q,
                    QuestionData.version == v,
                    QuestionData.status == "done",
                    Group.scanned == True,
                )
                .count()
            )
        except QuestionData.DoesNotExist:
            return 0

    def MgetDoneTasks(self, username, q, v):
        """When a id-client logs on they request a list of papers they have already Marked.
        Send back the list."""
        query = QuestionData.select().where(
            QuestionData.username == username,
            QuestionData.questionNumber == q,
            QuestionData.version == v,
            QuestionData.status == "done",
        )
        markList = []
        for x in query:
            markList.append([x.group.gid, x.status, x.mark, x.markingTime, x.tags])
        return markList

    def MgetNextTask(self, q, v):
        """Find unid'd test and send testNumber to client"""
        with plomdb.atomic():
            try:
                x = (
                    QuestionData.select()
                    .join(Group)
                    .where(
                        QuestionData.status == "todo",
                        QuestionData.questionNumber == q,
                        QuestionData.version == v,
                        Group.scanned == True,
                    )
                    .get()
                )
            except QuestionData.DoesNotExist as e:
                print("Nothing left on to-do pile - {}".format(e))
                return None

            print("Next marking task = {}".format(x.group.gid))
            return x.group.gid

    def MgiveTaskToClient(self, username, groupID):
        try:
            with plomdb.atomic():
                gref = Group.get_or_none(Group.gid == groupID)
                if gref.scanned == False:
                    return [False]
                qref = gref.questiondata[0]
                if qref.username != "" and qref.username != username:
                    # has been claimed by someone else.
                    return [False]
                # update status, Student-number, name, id-time.
                qref.status = "out"
                qref.username = username
                qref.time = datetime.now()
                qref.save()
                # return [true, tags, page1, page2, etc]
                rval = [
                    True,
                    qref.tags,
                ]
                for p in gref.pages.order_by(Page.pageNumber):
                    rval.append(p.fileName)
                print("Giving marking task {} to user {}".format(groupID, username))
                return rval
        except Group.DoesNotExist:
            print("That question {} not known".format(groupID))
            return False

    def MdidNotFinish(self, username, groupID):
        """When user logs off, any images they have still out should be put
        back on todo pile
        """
        # Log user returning given tgv.
        print("User {} did not mark task {}".format(username, groupID))
        try:
            with plomdb.atomic():
                gref = Group.get_or_none(Group.gid == groupID)
                if gref.scanned == False:
                    return
                qref = gref.questiondata[0]
                if qref.username != username or qref.status != "out":
                    # has been claimed by someone else.
                    return
                # update status, Student-number, name, id-time.
                qref.status = "todo"
                qref.username = ""
                qref.time = datetime.now()
                qref.markingTime = 0
                qref.marked = False
                qref.save()
                qref.test.marked = False
                qref.test.save()

        except Group.DoesNotExist:
            print("That task {} not known".format(groupID))
            return False

    def MtakeTaskFromClient(
        self, task, username, mark, aname, pname, cname, mtime, tags, md5
    ):
        """Get marked image back from client and update the record
        in the database.
        """
        try:
            with plomdb.atomic():
                gref = Group.get_or_none(Group.gid == task)
                qref = gref.questiondata[0]
                if qref.username != username:
                    # has been claimed by someone else.
                    return False

                # update status, mark, annotate-file-name, time, and
                # time spent marking the image
                qref.status = "done"
                qref.mark = mark
                qref.annotatedFile = aname
                qref.md5sum = md5
                qref.plomFile = pname
                qref.commentFile = cname
                qref.time = datetime.now()
                qref.markingTime = mtime
                qref.tags = tags
                qref.marked = True
                qref.save()
                # since this has been marked - check if all questions for test have been marked
                tref = qref.test
                # check if there are any unmarked questions
                if (
                    QuestionData.get_or_none(
                        QuestionData.test == tref, QuestionData.marked == False
                    )
                    is not None
                ):
                    print(
                        "Task {} marked {} by user {} and placed at {}".format(
                            task, mark, username, aname
                        )
                    )
                    return True
                # update the sum-mark
                tot = 0
                for qd in QuestionData.select().where(QuestionData.test == tref):
                    tot += qd.mark
                sref = tref.sumdata[0]
                sref.username = "automatic"
                sref.time = datetime.now()
                sref.sumMark = tot
                sref.summed = True
                sref.status = "done"
                sref.save()
                print(
                    "All of test {} is marked - total updated = {}".format(
                        tref.testNumber, tot
                    )
                )
                tref.marked = True
                tref.totalled = True
                tref.save()
                return True

        except Group.DoesNotExist:
            print(
                "That task number {} / username {} pair not known".format(
                    task, username
                )
            )
            return False

    def MgetImages(self, username, task):
        try:
            with plomdb.atomic():
                gref = Group.get_or_none(Group.gid == task)
                if gref.scanned == False:
                    return [False, "Task {} is not completely scanned".format(task)]
                qref = gref.questiondata[0]
                if qref.username != username:
                    # belongs to another user
                    return [
                        False,
                        "Task {} does not belong to user {}".format(task, username),
                    ]
                # return [true, n, page1,..,page.n]
                # or
                # return [true, n, page1,..,page.n, annotatedFile, plomFile]
                pp = []
                for p in gref.pages.order_by(Page.pageNumber):
                    pp.append(p.fileName)
                if qref.annotatedFile is not None:
                    return [True, len(pp)] + pp + [qref.annotatedFile, qref.plomFile]
                else:
                    return [True, len(pp)] + pp
        except Group.DoesNotExist:
            print("That task {} not known".format(task))
            return False

    def MgetOriginalImages(self, task):
        try:
            with plomdb.atomic():
                gref = Group.get(Group.gid == task)
                if gref.scanned == False:
                    return [False, "Task {} is not completely scanned".format(task)]
                qref = gref.questiondata[0]
                # return [true, page1,..,page.n]
                rval = [True]
                for p in gref.pages.order_by(Page.pageNumber):
                    rval.append(p.fileName)
                return rval
        except Group.DoesNotExist:
            return [False, "Task {} not known".format(task)]

    def MsetTag(self, username, task, tag):
        try:
            with plomdb.atomic():
                gref = Group.get(Group.gid == task)
                qref = gref.questiondata[0]
                if qref.username != username:
                    return False  # not your task
                # update tag
                qref.tags = tag
                qref.save()
                print("Task {} tagged {} by user {}".format(task, tag, username))
                return True
        except Group.DoesNotExist:
            print("That task {} / username {} pair not known".format(task, username))
            return False

    def MgetWholePaper(self, testNumber):
        tref = Test.get_or_none(Test.testNumber == testNumber, Test.scanned == True)
        if tref is None:  # don't know that test - this shouldn't happen
            return [False]
        pageFiles = []
        pageNames = []
        for pref in tref.pages:
            # Don't include ID-group pages
            if pref.group.groupType != "i":
                pageNames.append(pref.pageNumber)
                pageFiles.append(pref.fileName)
        return [True, pageNames] + pageFiles

    # ----- totaller stuff
    def TcountAll(self):
        """Count all the records"""
        try:
            return Test.select().where(Test.scanned == True).count()
        except Test.DoesNotExist:
            return 0

    def TcountTotalled(self):
        """Count all the records"""
        try:
            return (
                Test.select()
                .where(Test.totalled == True, Test.scanned == True,)
                .count()
            )
        except Test.DoesNotExist:
            return 0

    def TgetNextTask(self):
        """Find unid'd test and send testNumber to client"""
        with plomdb.atomic():
            try:
                x = SumData.get(SumData.status == "todo",)
            except SumData.DoesNotExist:
                print("Nothing left on to-do pile")
                return None

            print("Next Totalling task = {}".format(x.test.testNumber))
            return x.test.testNumber

    def TgetDoneTasks(self, username):
        """When a id-client logs on they request a list of papers they have already IDd.
        Send back the list."""
        query = SumData.select().where(
            SumData.username == username, SumData.status == "done"
        )
        tList = []
        for x in query:
            tList.append([x.test.testNumber, x.status, x.sumMark])
        return tList

    def TgiveTaskToClient(self, username, testNumber):
        try:
            with plomdb.atomic():
                tref = Test.get_or_none(Test.testNumber == testNumber)
                if tref.scanned == False:
                    return [False]
                sref = tref.sumdata[0]
                if sref.username != "" and sref.username != username:
                    # has been claimed by someone else.
                    return [False]
                # update status, Student-number, name, id-time.
                sref.status = "out"
                sref.username = username
                sref.time = datetime.now()
                sref.save()
                # return [true, page1]
                pref = Page.get(Page.test == tref, Page.pageNumber == 1)
                return [True, pref.fileName]
                print(
                    "Giving totalling task {} to user {}".format(testNumber, username)
                )
                return rval

        except Test.DoesNotExist:
            print("That test number {} not known".format(testNumber))
            return False

    def TdidNotFinish(self, username, testNumber):
        """When user logs off, any images they have still out should be put
        back on todo pile
        """
        # Log user returning given tgv.
        print("User {} did not total task {}".format(username, testNumber))
        try:
            with plomdb.atomic():
                tref = Test.get_or_none(Test.testNumber == testNumber)
                if tref.scanned == False:
                    return
                sref = tref.sumdata[0]
                if sref.username != username or sref.status != "out":
                    # has been claimed by someone else.
                    return
                # update status, Student-number, name, id-time.
                sref.status = "todo"
                sref.username = ""
                sref.time = datetime.now()
                sref.summed = False
                sref.save()
                tref.summed = False
                tref.save()
        except Test.DoesNotExist:
            print("That test number {} not known".format(testNumber))
            return False

    def TgetImage(self, username, t):
        tref = Test.get_or_none(Test.testNumber == t)
        if tref.scanned == False:
            return [False]
        sref = tref.sumdata[0]
        # check if task given to user
        if sref.username != username:
            return [False]
        pref = Page.get(Page.test == tref, Page.pageNumber == 1)
        print(
            "Sending cover-page of test {} to user {} = {}".format(
                t, username, pref.fileName
            )
        )
        return [True, pref.fileName]

    def TtakeTaskFromClient(self, testNumber, username, totalMark):
        print(
            "User {} returning totalled-task {} with {}".format(
                username, testNumber, totalMark
            )
        )
        try:
            with plomdb.atomic():
                tref = Test.get_or_none(Test.testNumber == testNumber)
                if tref.scanned == False:
                    return [False]
                sref = tref.sumdata[0]
                if sref.username != username:
                    # that belongs to someone else - this is a serious error
                    return [False]
                # update status, Student-number, name, id-time.
                sref.status = "done"
                sref.sumMark = totalMark
                sref.summed = True
                sref.time = datetime.now()
                sref.save()
                tref.totalled = True
                tref.save()
                return [True]
        except Test.DoesNotExist:
            print("That test number {} not known".format(testNumber))
            return [False]
