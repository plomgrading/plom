from peewee import *
from datetime import datetime

# import logging
# logger = logging.getLogger("peewee")
# logger.addHandler(logging.StreamHandler())
# logger.setLevel(logging.DEBUG)


plomdb = SqliteDatabase("../resources/plom.db")

# the test contains groups
# test bools something like
# produced = we've built the PDF
# scanned = we've fed it to students, scanned it into system.
# identified = ID-ing is done
# marked = marking is done
# finished = we've rebuilt the PDF at the end with coverpages etc etc


class Test(Model):
    testNumber = IntegerField(primary_key=True, unique=True)
    # some state bools
    produced = BooleanField(default=False)
    scanned = BooleanField(default=False)
    identified = BooleanField(default=False)
    marked = BooleanField(default=False)
    finished = BooleanField(default=False)
    hasCollisions = BooleanField(default=False)

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
    hasCollisions = BooleanField(default=False)

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
    mark = IntegerField(null=True)
    username = CharField(default="")
    time = DateTimeField(null=True)
    # flags
    marked = BooleanField(default=False)

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
    hasCollisions = BooleanField(default=False)

    class Meta:
        database = plomdb


# Colliding pages should be attached to the page their are duplicating
# When collision status resolved we can move them about.
class CollidingPages(Model):
    page = ForeignKeyField(Page, backref="collisions")
    originalName = CharField(null=True)
    fileName = CharField(null=True)
    md5sum = CharField()

    class Meta:
        database = plomdb


# Unknown pages are basically just the file
class UnknownPages(Model):
    originalName = CharField(null=True)
    fileName = CharField(null=True)
    md5sum = CharField()

    class Meta:
        database = plomdb


# Discarded pages are basically just the file and a reason
# reason could be "garbage", "duplicate of tpv-code", ...?
class DiscardedPages(Model):
    originalName = CharField(null=True)
    fileName = CharField(null=True)
    md5sum = CharField()
    reason = CharField()
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
                    Page,
                    UnknownPages,
                    CollidingPages,
                    DiscardedPages,
                ]
            )

    def createTest(self, t):
        try:
            Test.create(testNumber=t)  # must be unique
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
            iref.status = "identified"
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
            else:
                tref.scanned = False
            tref.save()

    def setGroupReady(self, gref):
        if gref.groupType == "i":
            iref = gref.iddata[0]
            # check if group already identified - can happen if printed tests with names
            if iref.status == "identified":
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
            qref = gref.questiondata[0]
            if qref.status is not "":
                print("We should never reach here - status = {}".format(qref.status))
            gref.status = "todo"
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
            self.checkGroupAllUploaded(pref)
            return [True, "success", "Page saved as {}".format(pref.pid)]

    def uploadUnknownPage(self, oname, nname, md5):
        # return value is either [True, <success message>] or
        # [False, <duplicate message>]
        # check if md5 is already in Unknown pages
        uref = UnknownPages.get_or_none(md5sum=md5)
        if uref is not None:
            return [
                False,
                "duplicate",
                "Exact duplicate of page already in database",
            ]
        with plomdb.atomic():
            uref = UnknownPages.create(originalName=oname, fileName=nname, md5sum=md5)
            uref.save()
        return [True, "success", "Page saved in unknownPages list"]

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
            cref = CollidingPages.create(
                originalName=oname, fileName=nname, md5sum=md5, page=pref
            )
            cref.save()
        self.flagCollisions(pref)
        return [
            True,
            "success",
            "Colliding page saved, attached to {}".format(pref.pid),
        ]

    def flagCollisions(self, pref):
        # TODO - Colin we need to think about this very carefully.
        with plomdb.atomic():
            pref.hasCollisions = True
            pref.save()

            gref = pref.group
            tref = gref.test
            if gref.groupType == "d":  # we don't care
                pass
            else:  # for either i or m groups the test is not finished.
                gref.hasCollisions = True
                gref.status = (
                    ""  # TODO - will this mess up any papers that are out with clients?
                )
                tref.hasCollisions = True
                tref.finished = False
                if gref.groupType == "i":  # if ID-group then invalidate any IDs
                    tref.identified = False
                    iref = gref.iddata[0]
                    iref.studentName = None
                    iref.studentID = None
                    iref.identified = False
                    iref.save()
                elif gref.groupType == "m":
                    # invalidate the marking
                    tref.marked = False
                    qref = gref.questiondata[0]
                    qref.marked = False
                    qref.mark = None
                    qref.annotatedFile = None
                    # should we delete that? - else move to DiscardedPages
                    qref.save()
                gref.save()
                tref.save()

    # ------------------
    # For user login - we reset all their stuff that is out

    def resetUsersToDo(self, username):
        with plomdb.atomic():
            query = IDData.select().where(
                IDData.username == username, IDData.status == "outforiding"
            )
            for x in query:
                x.status = "todo"
                x.username = ""
                x.time = datetime.now()
                x.save()
        with plomdb.atomic():
            query = QuestionData.select().where(
                QuestionData.username == username,
                QuestionData.status == "outformarking",
            )
            for x in query:
                x.status = "todo"
                x.username = ""
                x.markingTime = 0
                x.time = datetime.now()
                x.save()

    # ------------------
    # Identifier stuff
    # The ID-able tasks have grouptype ="i", group.scanned=True, group.collisions=false
    # The todo id-tasks are iddata.status="todo"
    # the done id-tasks have iddata.status="identified"

    def IDcountAll(self):
        """Count all the records"""
        try:
            return (
                Group.select()
                .where(
                    Group.groupType == "i",
                    Group.scanned == True,
                    Group.hasCollisions == False,
                )
                .count()
            )
        except Test.DoesNotExist:
            return 0

    def IDcountIdentified(self):
        """Count all the ID'd records"""
        """Count all the records"""
        try:
            return (
                Group.select()
                .join(IDData)
                .where(
                    Group.groupType == "i",
                    Group.scanned == True,
                    Group.hasCollisions == False,
                    IDData.identified == True,
                )
                .count()
            )
        except Test.DoesNotExist:
            return 0

    def IDgetNextTask(self):
        """Find unid'd test and send testNumber to client"""
        try:
            with plomdb.atomic():
                try:
                    x = (
                        IDData.select()
                        .join(Group)
                        .where(
                            IDData.status == "todo",
                            Group.scanned == True,
                            Group.hasCollisions == False,
                        )
                        .get()
                    )
                except IDData.DoesNotExist:
                    print("Nothing left on to-do pile")
                    return None

                print("Next ID task = {}".format(x.test.testNumber))
                return x.test.testNumber
        except Test.DoesNotExist:
            print("Nothing left on To-Do pile")
            return None

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
                iref.status = "outforiding"
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
        query = IDData.select().where(IDData.username == username)
        idList = []
        for x in query:
            if x.status == "identified":
                idList.append([x.test.testNumber, x.status, x.studentID, x.studentName])
        return idList

    def IDgetImage(self, username, t):
        tref = Test.get_or_none(Test.testNumber == t)
        if tref.scanned == False:
            return [False]
        iref = tref.iddata[0]
        # check if task given to user
        if iref.username != username:
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
        print("User {} did not ID-task {}".format(username, testNumber))
        try:
            with plomdb.atomic():
                tref = Test.get_or_none(Test.testNumber == testNumber)
                if tref.scanned == False:
                    return
                iref = tref.iddata[0]
                if iref.username != username or iref.status != "outforiding":
                    # has been claimed by someone else.
                    return
                # update status, Student-number, name, id-time.
                iref.status = "todo"
                iref.username = ""
                iref.time = datetime.now()
                iref.save()

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
                iref.status = "identified"
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
