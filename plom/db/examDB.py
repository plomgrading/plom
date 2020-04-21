from peewee import *
from datetime import datetime, timedelta
import logging

from plom.rules import censorStudentNumber as censorID
from plom.rules import censorStudentName as censorName


log = logging.getLogger("DB")
plomdb = SqliteDatabase(None)

######################################################################


class BaseModel(Model):
    class Meta:
        database = plomdb


class User(BaseModel):
    name = CharField(unique=True)
    enabled = BooleanField(default=True)
    password = CharField(null=True)  # hash of password for comparison
    token = CharField(null=True)  # authentication token
    lastActivity = DateTimeField(null=True)
    lastAction = CharField(null=True)


class Image(BaseModel):
    originalName = CharField(null=True)  # can be empty.
    fileName = CharField(null=True)
    md5sum = CharField(null=True)  # to check for duplications


class Test(BaseModel):
    testNumber = IntegerField(primary_key=True, unique=True)
    # some state bools
    produced = BooleanField(default=False)
    used = BooleanField(default=False)
    scanned = BooleanField(default=False)
    identified = BooleanField(default=False)
    marked = BooleanField(default=False)
    totalled = BooleanField(default=False)


# Data for totalling the marks
class SumData(BaseModel):
    test = ForeignKeyField(Test, backref="sumdata")
    sumMark = IntegerField(null=True)
    status = CharField(default="")
    user = ForeignKeyField(User, backref="sumdata", null=True)
    time = DateTimeField(null=True)


class Group(BaseModel):
    test = ForeignKeyField(Test, backref="groups")
    gid = CharField(unique=True)  # must be unique
    groupType = CharField()  # to distinguish between ID, DNM, and Mark groups
    queuePosition = IntegerField(unique=True, null=False)
    scanned = BooleanField(default=False)  # should get all its tpages


class IDGroup(BaseModel):
    test = ForeignKeyField(Test, backref="idgroup")
    group = ForeignKeyField(Group, backref="idgroup")
    studentID = CharField(unique=True, null=True)
    studentName = CharField(null=True)
    user = ForeignKeyField(User, backref="idgroup", null=True)
    status = CharField(default="")
    time = DateTimeField(null=True)


class DNMGroup(BaseModel):
    test = ForeignKeyField(Test, backref="dnmgroup")
    group = ForeignKeyField(Group, backref="dnmgroup")


class QGroup(BaseModel):
    test = ForeignKeyField(Test, backref="qgroup")
    group = ForeignKeyField(Group, backref="qgroup")
    question = IntegerField(null=False)
    version = IntegerField(null=False, default=1)
    user = ForeignKeyField(User, backref="idgroup", null=True)


class TPage(BaseModel):  # a test page that knows it tpgv
    test = ForeignKeyField(Test, backref="tpages")
    pageNumber = IntegerField(null=False)
    version = IntegerField(default=1)
    group = ForeignKeyField(Group, backref="tpages")
    image = ForeignKeyField(Image, backref="tpages", null=True)
    scanned = BooleanField(default=False)  # we should get all of them


class HWPage(BaseModel):  # a hw page that knows it tqv, but not p.
    test = ForeignKeyField(Test, backref="hwpages")
    group = ForeignKeyField(Group, backref="hwpages")
    order = IntegerField(null=False)
    version = IntegerField(default=1)  # infer from group
    image = ForeignKeyField(Image, backref="hwpages")


class XPage(BaseModel):  # a page that just knows it t.
    test = ForeignKeyField(Test, backref="xpages")
    order = IntegerField(null=False)
    image = ForeignKeyField(Image, backref="xpages")


class UnknownPage(BaseModel):
    image = ForeignKeyField(Image, backref="upages", null=True)


class CollidingPage(BaseModel):
    tpage = ForeignKeyField(TPage, backref="collisions")
    image = ForeignKeyField(Image, backref="collisions")


class DiscardedPage(BaseModel):
    image = ForeignKeyField(Image, backref="discards")
    reason = CharField(null=True)


class IDPage(BaseModel):
    idgroup = ForeignKeyField(IDGroup, backref="idpages")
    image = ForeignKeyField(Image, backref="idpages")
    order = IntegerField(null=False)


class DNMPage(BaseModel):
    dnmgroup = ForeignKeyField(DNMGroup, backref="dnmpages")
    image = ForeignKeyField(Image, backref="dnmpages")
    order = IntegerField(null=False)


class Annotation(BaseModel):
    qgroup = ForeignKeyField(QuestionData, backref="annotations")
    user = ForeignKeyField(User, backref="annotations", null=True)
    status = CharField(default="")
    image = ForeignKeyField(Image, backref="annotations", null=True)
    edition = IntegerField(null=True)
    # we need to order the annotations - want the latest.
    plomFile = CharField(null=True)
    commentFile = CharField(null=True)
    mark = IntegerField(null=True)
    markingTime = IntegerField(null=True)
    time = DateTimeField(null=True)
    tags = CharField(default="")


class APage(BaseModel):
    annotation = ForeignKeyField(Annotation, backref="apages")
    image = ForeignKeyField(Image, backref="apages")
    order = IntegerField(null=False)


class PlomDB:
    def __init__(self, dbFilename="plom.db"):
        # can't handle pathlib?
        plomdb.init(str(dbFilename))

        with plomdb:
            plomdb.create_tables(
                [
                    User,
                    Image,
                    Test,
                    ##
                    SumData,
                    ##
                    Group,
                    IDGroup,
                    DNMGroup,
                    QGroup,
                    ##
                    TPage,
                    HWPage,
                    XPage,
                    UnknownPage,
                    CollidingPage,
                    DiscardedPage,
                    ##
                    Annotation,
                    ##
                    APage,
                    IDPage,
                    DNMPage,
                ]
            )
        log.info("Database initialised.")
        # check if HAL has been created
        if User.get_or_none(name="HAL") is None:
            User.create(
                name="HAL",
                password=None,
                lastActivity=datetime.now(),
                lastAction="Created",
            )
            log.info("User 'HAL' created to do all our automated tasks.")

    ########### User stuff #############
    def createUser(self, uname, passwordHash):
        try:
            uref = User.create(
                name=uname,
                password=passwordHash,
                lastActivity=datetime.now(),
                lastAction="Created",
            )
        except IntegrityError as e:
            log.error("Create User {} error - {}".format(uname, e))
            return False
        return True

    def doesUserExist(self, uname):
        uref = User.get_or_none(name=uname)
        if uref is None:
            return False
        else:
            return True

    def setUserPasswordHash(self, uname, passwordHash):
        # Don't mess with HAL
        if uname == "HAL":
            return False
        # token generated by server not DB
        uref = User.get_or_none(name=uname)
        if uref is None:
            return False
        with plomdb.atomic():
            uref.password = passwordHash
            uref.lastActivity = datetime.now()
            uref.lastAction = "Password set"
            uref.save()
        return True

    def getUserPasswordHash(self, uname):
        uref = User.get_or_none(name=uname)
        if uref is None:
            return None
        else:
            return uref.password

    def isUserEnabled(self, uname):
        uref = User.get_or_none(name=uname)
        if uref is None:
            return False
        else:
            return uref.enabled

    def enableUser(self, uname):
        uref = User.get_or_none(name=uname)
        if uref is None:
            return False
        with plomdb.atomic():
            uref.enabled = True
            uref.save()
        return True

    def disableUser(self, uname):
        # when user is disabled we should set the enabled flag to false, remove their auth-token and then remove all their todo-stuff.
        uref = User.get_or_none(name=uname)
        if uref is None:
            return False
        # set enabled flag to false and remove their token
        with plomdb.atomic():
            uref.enabled = False
            uref.token = None
            uref.save()
        # put all of user's tasks back on the todo pile.
        self.resetUsersToDo(uname)
        return True

    def setUserToken(self, uname, token, msg="Log on"):
        # token generated by server not DB
        uref = User.get_or_none(name=uname)
        if uref is None:
            return False
        with plomdb.atomic():
            uref.token = token
            uref.lastActivity = datetime.now()
            uref.lastAction = msg
            uref.save()
        return True

    def clearUserToken(self, uname):
        return self.setUserToken(uname, None, "Log off")

    def getUserToken(self, uname):
        uref = User.get_or_none(name=uname)
        if uref is None:
            return None
        else:
            return uref.token

    def userHasToken(self, uname):
        if self.getUserToken(uname) is not None:
            return True
        else:
            return False

    def validateToken(self, uname, token):
        uref = User.get_or_none(name=uname)
        if uref is None:
            return False
        if uref.token == token:
            return True
        else:
            return False

    def getUserList(self):
        rval = []
        for uref in User.select():
            rval.append(uref.name)
        return rval

    def getUserDetails(self):
        rval = {}
        for uref in User.select():
            val = [False, False]
            if uref.enabled:
                val[0] = True
            if uref.token is not None:
                val[1] = True
            if uref.lastActivity is None:
                val += ["", ""]
            else:
                val += [
                    uref.lastActivity.strftime("%y:%m:%d-%H:%M:%S"),
                    uref.lastAction,
                ]
            rval[uref.name] = val + self.RgetUserFullProgress(uref.name)
        return rval

    ########## Test creation stuff ##############
    def nextQueuePosition(self):
        lastPos = Group.select(fn.MAX(Group.queuePosition)).scalar()
        if lastPos is None:
            return 0
        else:
            return lastPos + 1

    def createTest(self, t):
        try:
            tref = Test.create(testNumber=t)  # must be unique
            sref = SumData.create(test=tref)  # also create the sum-data
        except IntegrityError as e:
            log.error("Create test {} error - {}".format(t, e))
            return False
        return True

    def addTestPages(self, tref, gref, t, pages, v):
        flag = True
        with plomdb.atomic():
            for p in pages:
                try:
                    TPage.create(
                        test=tref,
                        group=gref,
                        pageNumber=p,
                        version=v,
                        pid="t{}p{}".format(t, p),
                        scanned=False,
                    )
                except IntegrityError as e:
                    log.error("Adding page {} for test {} error - {}".format(p, t, e))
                    flag = False
        return flag

    def createIDGroup(self, t, pages):
        tref = Test.get_or_none(testNumber=t)

        if tref is None:
            log.warning("Create ID - No test with number {}".format(t))
            return False

        gid = "i{}".format(str(t).zfill(4))
        try:
            gref = Group.create(
                test=tref,
                gid=gid,
                groupType="i",
                queuePosition=self.nextQueuePosition(),
            )  # must be unique
        except IntegrityError as e:
            log.error(
                "Create ID - cannot create group {} of test {} error - {}".format(
                    gid, t, e
                )
            )
            return False
        try:
            iref = IDData.create(test=tref, group=gref)
        except IntegrityError as e:
            log.error(
                "Create ID - cannot create IDData {} of group {} error - {}.".format(
                    qref, gref, e
                )
            )
            return False
        return self.addTestPages(tref, gref, t, pages, 1)

    def createDNMGroup(self, t, pages):
        tref = Test.get_or_none(testNumber=t)
        if tref is None:
            log.warning("Create DNM - No test with number {}".format(t))
            return False

        gid = "d{}".format(str(t).zfill(4))
        # make the dnmgroup
        try:
            # A DNM group may have 0 pages, in that case mark it as scanned and set status = "complete"
            sc = True if len(pages) == 0 else False
            gref = Group.create(
                test=tref,
                gid=gid,
                groupType="d",
                scanned=sc,
                queuePosition=self.nextQueuePosition(),
            )

        except IntegrityError as e:
            log.error(
                "Create DNM - cannot make Group {} of Test {} error - {}".format(
                    gid, t, e
                )
            )
            return False
        return self.addTestPages(tref, gref, t, pages, 1)

    def createQGroup(self, t, g, v, pages):
        tref = Test.get_or_none(testNumber=t)
        if tref is None:
            log.warning("Create Q - No test with number {}".format(t))
            return False

        gid = "m{}g{}".format(str(t).zfill(4), g)
        # make the mgroup
        try:
            gref = Group.create(
                test=tref,
                gid=gid,
                groupType="m",
                version=v,
                queuePosition=self.nextQueuePosition(),
            )
        except IntegrityError as e:
            log.error(
                "Create Q - cannot create group {} of Test {} error - {}".format(
                    gid, t, e
                )
            )
            return False
        try:
            qref = QuestionData.create(
                test=tref, group=gref, questionNumber=g, version=v
            )
        except IntegrityError as e:
            log.error(
                "Create Q - cannot create QuestionData {} of question {} error - {}.".format(
                    qref, gid, e
                )
            )
            return False
        try:
            aref = Annotation.create(qdata=qref, edition=0)
        except IntegrityError as e:
            log.error(
                "Create A - cannot create Annotation {} of question {} {}.".format(
                    aref, qref, e
                )
            )
            return False

        return self.addTestPages(tref, gref, t, pages, v)

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

    def printProducedPagesByTest(self, t):
        tref = Test.get_or_none(testNumber=t)
        if tref is None:
            return
        for p in tref.prodpages.order_by(ProducedPage.pageNumber):
            print(p.pageNumber, p.version, p.group.gid)

    def getProducedPageVersions(self, t):
        tref = Test.get_or_none(testNumber=t)
        if tref is None:
            return {}
        else:
            pvDict = {p.pageNumber: p.version for p in tref.testpages}
            return pvDict

    def produceTest(self, t):
        # After creating the test (plom-build) we'll turn the spec'd papers into PDFs
        # we'll refer to those as "produced"
        tref = Test.get_or_none(testNumber=t)
        if tref is None:
            log.error('Cannot set test {} to "produced" - it does not exist'.format(t))
            return
        else:
            # TODO - work out how to make this more efficient? Multiple updates in one op?
            with plomdb.atomic():
                tref.produced = True
                tref.save()
            log.info('Test {} is set to "produced"'.format(t))

    def identifyTest(self, t, sid, sname):
        tref = Test.get_or_none(testNumber=t)
        if tref is None:
            return
        iref = IDData.get_or_none(test=tref)
        if iref is None:
            return
        autref = User.get(name="HAL")
        with plomdb.atomic():
            iref.status = "done"
            iref.studentID = sid
            iref.studentName = sname
            iref.identified = True
            iref.user = autref
            iref.time = datetime.now()
            iref.save()
            tref.identified = True
            tref.save()
        log.info("Test {} id'd as {} {}".format(t, censorID(sid), censorName(sname)))

    def checkTestAllUploaded(self, gref):
        tref = gref.test
        sflag = True
        for g in tref.groups:
            if g.scanned == False:
                # TODO - deal with empty DO NOT MARK groups correctly
                sflag = False
                log.debug(
                    "Check: Test {} not yet fully scanned: (at least) {} not present".format(
                        tref.testNumber, g.gid
                    )
                )
                break
        with plomdb.atomic():
            if sflag:
                tref.scanned = True
                log.info(
                    "Check uploaded - Test {} is now fully scanned".format(
                        tref.testNumber
                    )
                )
                # set the status of the sumdata
                sdref = tref.sumdata[0]
                sdref.status = "todo"
                sdref.save()
            else:
                tref.scanned = False
            tref.save()

    def setGroupReady(self, gref):
        log.debug("All of group {} is scanned".format(gref.gid))
        if gref.groupType == "i":
            iref = gref.iddata[0]
            # check if group already identified - can happen if printed tests with names
            if iref.status == "done":
                log.info("Group {} is already identified.".format(gref.gid))
            else:
                iref.status = "todo"
                log.info("Group {} is ready to be identified.".format(gref.gid))
            iref.save()
        elif gref.groupType == "d":
            # we don't do anything with these groups
            log.info(
                "Group {} is DoNotMark - all scanned, nothing to be done.".format(
                    gref.gid
                )
            )
        elif gref.groupType == "m":
            log.info("Group {} is ready to be marked.".format(gref.gid))
            qref = gref.questiondata[0]
            qref.status = "todo"
            qref.save()
        else:
            raise ValueError("Tertium non datur: should never happen")

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
            log.info(
                "Replacing missing page tpv = {}.{}.{} with {}".format(t, p, v, oname),
            )
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
            DiscardedPage.create(
                fileName=nname, originalName=pref.originalName, md5sum=pref.md5sum
            )
            pref.scanned = False
            pref.originalName = None
            pref.fileName = None
            pref.md5sum = None
            pref.scanned = False
            pref.save()
        log.info("Removing scanned page with fname = {}".format(fname))

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
        log.info("Invalidated dnm {}".format(gref.gid))
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
            iref.user = None
            iref.time = datetime.now()
            iref.studentID = None
            iref.studentName = None
            iref.save()
        log.info("Invalidated iddata {}".format(gref.gid))
        return []

    def invalidateQGroup(self, tref, gref, delPage=True):
        # When we delete a page, set "scanned" to false for group+test
        # If we are adding a page then we don't have to do that.
        qref = gref.questiondata[0]
        sref = tref.sumdata[0]
        rval = []
        with plomdb.atomic():
            # update the test
            if delPage:
                tref.scanned = False
            tref.marked = False
            tref.totalled = False
            tref.finished = False
            tref.save()
            # update the group
            if delPage:
                gref.scanned = False
                gref.save()
            # update the sumdata
            sref.status = ""
            sref.sumMark = None
            sref.user = None
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
            qref.user = None
            qref.time = datetime.now()
            qref.save
        log.info("Invalidated question {}".format(gref.gid))
        return rval

    def uploadKnownPage(self, t, p, v, oname, nname, md5):
        # return value is either [True, <success message>] or
        # [False, stuff] - but need to distinguish between "discard this image" and "you should perhaps keep this image"
        # So return either [False, "discard", discard message]
        # or [False, "keep", keep this image message]
        tref = Test.get_or_none(testNumber=t)
        if tref is None:
            return [False, "testError", "Cannot find test {}".format(t)]
        pref = TestPage.get_or_none(test=tref, pageNumber=p, version=v)
        if pref is None:
            return [
                False,
                "pageError",
                "Cannot find testpage,version {} for test {}".format([p, v], t),
            ]
        if pref.scanned:
            # have already loaded an image for this page - so this is actually a duplicate
            log.debug("This appears to be a duplicate. Checking md5sums")
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
                pref.image = Image.create(
                    originalName=oname, fileName=nname, md5sum=md5
                )
                pref.save()
                tref.used = True
                tref.save()
            log.info("Uploaded image {} to tpv = {}.{}.{}".format(oname, t, p, v))
            # self.checkGroupAllUploaded(pref)
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
        log.info("Uploaded image {} as unknown".format(oname))
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
        log.info(
            "Uploaded image {} as collision of tpv={}.{}.{}".format(oname, t, p, v)
        )
        return [
            True,
            "success",
            "Colliding page saved, attached to {}".format(pref.pid),
        ]

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
            if p.scanned == True:
                rval.append(p.fileName)
        return rval

    def checkPage(self, testNumber, pageNumber):
        tref = Test.get_or_none(Test.testNumber == testNumber)
        if tref is None:
            return [False]
        pref = Page.get_or_none(Page.test == tref, Page.pageNumber == pageNumber)
        if pref is None:
            return [False]
        if pref.scanned:  # we have a collision
            return [True, pref.version, pref.fileName]
        else:  # no collision since the page hasn't been scanned yet
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
        log.info("Removing unknown {} to discard {}".format(fname, nname))
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
        log.info("Removing collision {} to discard {}".format(fname, nname))
        return True

    def moveUnknownToPage(self, fname, nname, testNumber, pageNumber):
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
            pref.fileName = nname
            pref.md5sum = uref.md5sum
            pref.originalName = uref.originalName
            pref.scanned = True
            pref.save()
            uref.delete_instance()
        log.info(
            "Moving unknown {} to image {} of tp {}.{}".format(
                fname, nname, testNumber, pageNumber
            )
        )
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
        log.info(
            "Moving unknown {} to collision {} of tp {}.{}".format(
                fname, nname, testNumber, pageNumber
            )
        )
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
        log.info(
            "Collision {} replacing tpv {}.{}.{} as {}".format(
                fname, testNumber, pageNumber, version, nname
            )
        )
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
        log.info(
            "Saving extra {} as {} tp {}.{} of question {}".format(
                fname, nname, testNumber, pageNumber, questionNumber
            )
        )
        ## Now invalidate any work on the associated group
        # now update the group and keep list of files to delete potentially
        return [True, self.invalidateQGroup(tref, qref.group, delPage=False)]

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
        log.info("Moving discard {} back to unknown {}".format(fname, nname))
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
        log.debug("Sending list of scanned tests")
        return rval

    def RgetIncompleteTests(self):
        rval = {}
        for tref in Test.select().where(Test.scanned == False, Test.used == True):
            pState = []
            for p in tref.pages:
                pState.append([p.pageNumber, p.version, p.scanned])
            rval[tref.testNumber] = pState
        log.debug("Sending list of incomplete tests")
        return rval

    def RgetUnusedTests(self):
        rval = []
        for tref in Test.select().where(Test.used == False):
            rval.append(tref.testNumber)
        log.debug("Sending list of unused tests")
        return rval

    def RgetIdentified(self):
        rval = {}
        for iref in IDData.select().where(IDData.identified == True):
            rval[iref.test.testNumber] = (iref.studentID, iref.studentName)
        log.debug("Sending list of identified tests")
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

        log.debug("Sending progress summary for Q{}v{}".format(q, v))
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
            # make sure user.name and mark both in histogram
            if x.user.name not in rhist:
                rhist[x.user.name] = {}
            if x.mark not in rhist[x.user.name]:
                rhist[x.user.name][x.mark] = 0
            rhist[x.user.name][x.mark] += 1
        log.debug("Sending mark histogram for Q{}v{}".format(q, v))
        return rhist

    def RgetQuestionUserProgress(self, q, v):
        # return [ nScanned, [user, nmarked], [user, nmarked], etc]
        rdat = {}
        nScan = 0
        for x in (
            QuestionData.select()
            .join(Group)
            .where(
                QuestionData.questionNumber == q,
                QuestionData.version == v,
                Group.scanned == True,
            )
        ):
            nScan += 1
            if x.marked == True:
                if x.user.name not in rdat:
                    rdat[x.user.name] = 0
                rdat[x.user.name] += 1
        rval = [nScan]
        for x in rdat:
            rval.append([x, rdat[x]])
        log.debug("Sending question/user progress for Q{}v{}".format(q, v))
        return rval

    def RgetCompletions(self):
        rval = {}
        for tref in Test.select().where(Test.scanned == True):
            numMarked = (
                QuestionData.select()
                .where(QuestionData.test == tref, QuestionData.marked == True)
                .count()
            )
            rval[tref.testNumber] = [tref.identified, tref.totalled, numMarked]
        log.debug("Sending list of completed tests")
        return rval

    def RgetOutToDo(self):
        # return list of tasks that are status = todo
        # note - have to format the time as string since not jsonable.
        # x.time.strftime("%y:%m:%d-%H:%M:%S"),

        rval = []
        for iref in IDData.select().where(IDData.status == "out"):
            rval.append(
                [
                    "id-t{}".format(iref.test.testNumber),
                    iref.user.name,
                    iref.time.strftime("%y:%m:%d-%H:%M:%S"),
                ]
            )
        for mref in QuestionData.select().where(QuestionData.status == "out"):
            rval.append(
                [
                    "mrk-t{}-q{}-v{}".format(
                        mref.test.testNumber, mref.questionNumber, mref.version
                    ),
                    mref.user.name,
                    mref.time.strftime("%y:%m:%d-%H:%M:%S"),
                ]
            )
        for sref in SumData.select().where(SumData.status == "out"):
            rval.append(
                [
                    "tot-t{}".format(sref.test.testNumber),
                    sref.user.name,
                    sref.time.strftime("%y:%m:%d-%H:%M:%S"),
                ]
            )
        log.debug("Sending list of tasks that are still out")
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
            rval["iwho"] = iref.user.name
        if tref.totalled:
            sref = tref.sumdata[0]
            rval["total"] = sref.sumMark
            rval["twho"] = sref.user.name
        for qref in tref.questiondata:
            rval[qref.questionNumber] = {
                "marked": qref.marked,
                "mark": qref.mark,
                "version": qref.version,
                "who": qref.user.name,
            }

        log.debug("Sending status of test {}".format(testNumber))
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
        log.debug("Sending spreadsheet (effectively)")
        return rval

    def RgetOriginalFiles(self, testNumber):
        rval = []
        tref = Test.get_or_none(testNumber=testNumber)
        if tref is None:
            return []
        for p in tref.pages.order_by(Page.pageNumber):
            rval.append(p.fileName)
        log.debug("Sending original images of test {}".format(testNumber))
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
        log.debug("Sending coverpage info of test {}".format(testNumber))
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
        log.debug("Sending annotated images for test {}".format(testNumber))
        return rval

    def RgetMarkReview(self, filterQ, filterV, filterU):
        query = QuestionData.select().where(QuestionData.marked == True)
        if filterQ != "*":
            query = query.where(QuestionData.questionNumber == filterQ)
        if filterV != "*":
            query = query.where(QuestionData.version == filterV)
        if filterU != "*":
            query = query.where(QuestionData.user.name == filterU)
        rval = []
        for x in query:
            rval.append(
                [
                    x.test.testNumber,
                    x.questionNumber,
                    x.version,
                    x.mark,
                    x.user.name,
                    x.markingTime,
                    # CANNOT JSON DATETIMEFIELD.
                    x.time.strftime("%y:%m:%d-%H:%M:%S"),
                ]
            )
        log.debug(
            "Sending filtered mark-review data. filters (Q,V,U)={}.{}.{}".format(
                filterQ, filterV, filterU
            )
        )
        return rval

    def RgetAnnotatedImage(self, testNumber, questionNumber, version):
        tref = Test.get_or_none(testNumber=testNumber)
        if tref is None:
            return [False]
        qref = QuestionData.get_or_none(
            QuestionData.test == tref,
            QuestionData.questionNumber == questionNumber,
            QuestionData.version == version,
            QuestionData.marked == True,
        )
        if qref is None:
            return [False]
        log.debug(
            "Sending annotated image of tqv {}.{}.{}".format(
                testNumber, questionNumber, version
            )
        )
        return [True, qref.annotatedFile]

    def RgetIDReview(self):
        rval = []
        query = IDData.select().where(IDData.identified == True)
        for x in query:
            rval.append(
                [
                    x.test.testNumber,
                    x.user.name,
                    x.time.strftime("%y:%m:%d-%H:%M:%S"),
                    x.studentID,
                    x.studentName,
                ]
            )
        log.debug("Sending ID review data")
        return rval

    def RgetTotReview(self):
        rval = []
        query = SumData.select().where(SumData.summed == True)
        for x in query:
            rval.append(
                [
                    x.test.testNumber,
                    x.user.name,
                    x.time.strftime("%y:%m:%d-%H:%M:%S"),
                    x.sumMark,
                ]
            )
        log.debug("Sending totalling review data")
        return rval

    def RgetUserFullProgress(self, uname):
        uref = User.get_or_none(name=uname)
        if uref is None:
            return []
        # return [#IDd, #tot, #marked]
        log.debug("Sending user {} progress data".format(uname))
        return [
            IDData.select()
            .where(IDData.user == uref, IDData.identified == True)
            .count(),
            SumData.select()
            .where(SumData.user == uref, SumData.summed == True)
            .count(),
            QuestionData.select()
            .where(QuestionData.user == uref, QuestionData.marked == True)
            .count(),
        ]

    # ------------------
    # For user login - we reset all their stuff that is out

    def resetUsersToDo(self, uname):
        uref = User.get_or_none(name=uname)
        if uref is None:
            return
        with plomdb.atomic():
            query = IDData.select().where(IDData.user == uref, IDData.status == "out")
            for x in query:
                x.status = "todo"
                x.user = None
                x.time = datetime.now()
                x.save()
                log.info("Reset user {} ID task {}".format(uname, x.group.gid))
        with plomdb.atomic():
            query = Annotation.select().where(
                Annotation.user == uref, Annotation.status == "out",
            )
            for x in query:
                x.status = "todo"
                x.user = None
                x.markingTime = 0
                x.time = datetime.now()
                x.save()
                log.info(
                    "Reset user {} question-annotation task {}".format(
                        uname, x.qdata.group.gid
                    )
                )
        with plomdb.atomic():
            query = SumData.select().where(
                SumData.user == uref, SumData.status == "out"
            )
            for x in query:
                x.status = "todo"
                x.user = None
                x.time = datetime.now()
                x.save()
                log.info("Reset user {} totalling task {}".format(uname, x.group.gid))

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
                log.info("Nothing left on ID to-do pile")
                return None

            log.debug("Next ID task = {}".format(x.test.testNumber))
            return x.test.testNumber

    def IDgiveTaskToClient(self, uname, testNumber):
        uref = User.get(name=uname)
        # since user authenticated, this will always return legit ref.

        try:
            with plomdb.atomic():
                tref = Test.get_or_none(Test.testNumber == testNumber)
                if tref is None:
                    return [False]
                iref = tref.iddata[0]
                # verify the id-group has been scanned - it should always be scanned.if we get here.
                if iref.group.scanned == False:
                    return [False]
                if iref.user is not None and iref.user != uref:
                    # has been claimed by someone else.
                    return [False]
                # update status, Student-number, name, id-time.
                iref.status = "out"
                iref.user = uref
                iref.time = datetime.now()
                iref.save()
                # update user activity
                uref.lastAction = "Took ID task {}".format(testNumber)
                uref.lastActivity = datetime.now()
                uref.save()
                # return [true, page1, page2, etc]
                gref = iref.group
                rval = [True]
                for p in gref.pages.order_by(Page.pageNumber):
                    rval.append(p.fileName)
                log.debug("Giving ID task {} to user {}".format(testNumber, uname))
                return rval

        except Test.DoesNotExist:
            log.info("ID task - That test number {} not known".format(testNumber))
            return False

    def IDgetDoneTasks(self, uname):
        """When a id-client logs on they request a list of papers they have already IDd.
        Send back the list."""
        uref = User.get(name=uname)
        # since user authenticated, this will always return legit ref.

        query = IDData.select().where(IDData.user == uref, IDData.status == "done")
        idList = []
        for x in query:
            idList.append([x.test.testNumber, x.status, x.studentID, x.studentName])
        log.debug("Sending completed ID tasks to user {}".format(uname))
        return idList

    def IDgetImage(self, uname, t):
        uref = User.get(name=uname)
        # since user authenticated, this will always return legit ref.

        tref = Test.get_or_none(Test.testNumber == t)
        if tref.scanned == False:
            return [False]
        iref = tref.iddata[0]
        # quick sanity check to make sure task given to user, (or if manager making request)
        if iref.user == uref or uname == "manager":
            pass
        else:
            return [False]
        gref = iref.group
        rval = [True]
        for p in gref.pages.order_by(Page.pageNumber):
            rval.append(p.fileName)
        log.debug("Sending IDpages of test {} to user {}".format(t, uname))
        return rval

    def IDgetImageList(self, imageNumber):
        rval = {}
        query = IDData.select()
        for iref in query:
            # for each iref, check that it is scanned and then grab page.
            gref = iref.group
            if not gref.scanned:
                continue
            # make a list of all the pages in the IDgroup
            pages = []
            for p in gref.pages.order_by(Page.pageNumber):
                pages.append(p.fileName)
            # grab the relevant page if there.
            if len(pages) > imageNumber:
                rval[iref.test.testNumber] = pages[imageNumber]
        return rval

    def IDdidNotFinish(self, uname, testNumber):
        """When user logs off, any images they have still out should be put
        back on todo pile
        """
        uref = User.get(name=uname)
        # since user authenticated, this will always return legit ref.

        # Log user returning given tgv.
        with plomdb.atomic():
            tref = Test.get_or_none(Test.testNumber == testNumber)
            if tref is None:
                log.info("That test number {} not known".format(testNumber))
                return False

            if tref.scanned == False:
                return
            iref = tref.iddata[0]
            # sanity check that user has task
            if iref.user == uref and iref.status == "out":
                pass
            else:  # someone else has it, or it is not out.
                return
            # update status, Student-number, name, id-time.
            iref.status = "todo"
            iref.user = None
            iref.time = datetime.now()
            iref.identified = False
            iref.save()
            tref.identified = False
            tref.save()
            log.info("User {} did not ID task {}".format(uname, testNumber))

    def IDtakeTaskFromClient(self, testNumber, uname, sid, sname):
        """Get ID'dimage back from client - update record in database."""
        uref = User.get(name=uname)
        # since user authenticated, this will always return legit ref.

        try:
            with plomdb.atomic():
                tref = Test.get_or_none(Test.testNumber == testNumber)
                if tref is None:
                    return [False, False]
                iref = tref.iddata[0]
                # verify the id-group has been scanned - it should always be scanned.if we get here.
                if iref.group.scanned == False:
                    return [False, False]

                if iref.user != uref:
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
                # update user activity
                uref.lastAction = "Returned ID task {}".format(testNumber)
                uref.lastActivity = datetime.now()
                uref.save()
                return [True]
                log.info(
                    'User "{}" returning ID-task "{}" with "{}" "{}"'.format(
                        uname, testNumber, censorID(sid), censorName(sname)
                    )
                )
        except IDData.DoesNotExist:
            log.error("ID take task - That test number {} not known".format(testNumber))
            return [False, False]
        except IntegrityError:
            log.error(
                "ID take task - Student number {} already entered".format(censorID(sid))
            )
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

    def IDreviewID(self, testNumber):
        # shift ownership to "reviewer"
        revref = User.get(name="reviewer")  # should always be there

        tref = Test.get_or_none(Test.testNumber == testNumber)
        if tref is None:
            return [False]
        iref = IDData.get_or_none(IDData.test == tref, IDData.identified == True,)
        if iref is None:
            return [False]
        with plomdb.atomic():
            iref.user = revref
            iref.time = datetime.now()
            iref.save()
        log.info("ID task {} set for review".format(testNumber))
        return [True]

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

    def MgetDoneTasks(self, uname, q, v):
        """When a id-client logs on they request a list of papers they have already Marked.
        Send back the list."""
        uref = User.get(name=uname)  # authenticated, so not-None

        query = QuestionData.select().where(
            QuestionData.user == uref,
            QuestionData.questionNumber == q,
            QuestionData.version == v,
            QuestionData.status == "done",
        )
        markList = []
        for x in query:
            markList.append([x.group.gid, x.status, x.mark, x.markingTime, x.tags])
        log.debug('Sending completed Q{}v{} tasks to user "{}"'.format(q, v, uname))
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
                log.info("Nothing left on Q{}v{} to-do pile".format(q, v))
                return None

            log.debug("Next Q{}v{} task = {}".format(q, v, x.group.gid))
            return x.group.gid

    def MgiveTaskToClient(self, uname, groupID):
        uref = User.get(name=uname)  # authenticated, so not-None
        try:
            with plomdb.atomic():
                gref = Group.get_or_none(Group.gid == groupID)
                if gref.scanned == False:
                    return [False]
                qref = gref.questiondata[0]
                if qref.user is None or qref.user == uref:
                    pass
                else:  # has been claimed by someone else.
                    return [False]
                # update status, Student-number, name, id-time.
                qref.status = "out"
                qref.user = uref
                qref.time = datetime.now()
                qref.save()
                # update user activity
                uref.lastAction = "Took M task {}".format(groupID)
                uref.lastActivity = datetime.now()
                uref.save()
                # return [true, tags, page1, page2, etc]
                rval = [
                    True,
                    qref.tags,
                ]
                for p in gref.pages.order_by(Page.pageNumber):
                    rval.append(p.fileName)
                log.debug('Giving marking task {} to user "{}"'.format(groupID, uname))
                return rval
        except Group.DoesNotExist:
            log.info("That question {} not known".format(groupID))
            return False

    def MdidNotFinish(self, uname, groupID):
        """When user logs off, any images they have still out should be put
        back on todo pile
        """
        uref = User.get(name=uname)  # authenticated, so not-None

        try:
            with plomdb.atomic():
                gref = Group.get_or_none(Group.gid == groupID)
                if gref.scanned == False:
                    return
                qref = gref.questiondata[0]
                # sanity check that user has task
                if qref.user == uref and qref.status == "out":
                    pass
                else:  # has been claimed by someone else.
                    return

                # update status, Student-number, name, id-time.
                qref.status = "todo"
                qref.user = None
                qref.time = datetime.now()
                qref.markingTime = 0
                qref.marked = False
                qref.save()
                qref.test.marked = False
                qref.test.save()
                # Log user returning given tgv.
                log.info("User {} did not mark task {}".format(uname, groupID))

        except Group.DoesNotExist:
            log.info("That task {} not known".format(groupID))
            return False

    def MtakeTaskFromClient(
        self, task, uname, mark, aname, pname, cname, mtime, tags, md5
    ):
        """Get marked image back from client and update the record
        in the database.
        """
        uref = User.get(name=uname)  # authenticated, so not-None
        try:
            with plomdb.atomic():
                gref = Group.get_or_none(Group.gid == task)
                qref = gref.questiondata[0]

                if qref.user != uref:
                    return False  # has been claimed by someone else.

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
                # update user activity
                uref.lastAction = "Returned M task {}".format(task)
                uref.lastActivity = datetime.now()
                uref.save()
                # since this has been marked - check if all questions for test have been marked
                log.info(
                    "Task {} marked {} by user {} and placed at {} with md5 = {}".format(
                        task, mark, uname, aname, md5
                    )
                )
                tref = qref.test
                # check if there are any unmarked questions
                if (
                    QuestionData.get_or_none(
                        QuestionData.test == tref, QuestionData.marked == False
                    )
                    is not None
                ):
                    return True
                # update the sum-mark
                tot = 0
                for qd in QuestionData.select().where(QuestionData.test == tref):
                    tot += qd.mark
                sref = tref.sumdata[0]
                autref = User.get(name="HAL")
                sref.user = autref  # auto-totalled by HAL.
                sref.time = datetime.now()
                sref.sumMark = tot
                sref.summed = True
                sref.status = "done"
                sref.save()
                log.info(
                    "All of test {} is marked - total updated = {}".format(
                        tref.testNumber, tot
                    )
                )
                tref.marked = True
                tref.totalled = True
                tref.save()
                return True

        except Group.DoesNotExist:
            log.error(
                "That returning marking task number {} / user {} pair not known".format(
                    task, uname
                )
            )
            return False

    def MgetImages(self, uname, task):
        uref = User.get(name=uname)  # authenticated, so not-None
        try:
            with plomdb.atomic():
                gref = Group.get_or_none(Group.gid == task)
                if gref.scanned == False:
                    return [False, "Task {} is not completely scanned".format(task)]
                qref = gref.questiondata[0]
                if qref.user != uref:
                    # belongs to another user
                    return [
                        False,
                        "Task {} does not belong to user {}".format(task, uname),
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
            log.info("Mgetimage - task {} not known".format(task))
            return False

    def MgetOriginalImages(self, task):
        try:
            with plomdb.atomic():
                gref = Group.get(Group.gid == task)
                if gref.scanned == False:
                    log.warning(
                        "MgetOriginalImages - task {} not completely scanned".format(
                            task
                        )
                    )
                    return [False, "Task {} is not completely scanned".format(task)]
                qref = gref.questiondata[0]
                # return [true, page1,..,page.n]
                rval = [True]
                for p in gref.pages.order_by(Page.pageNumber):
                    rval.append(p.fileName)
                return rval
        except Group.DoesNotExist:
            log.info("MgetOriginalImages - task {} not known".format(task))
            return [False, "Task {} not known".format(task)]

    def MsetTag(self, uname, task, tag):
        uref = User.get(name=uname)  # authenticated, so not-None

        try:
            with plomdb.atomic():
                gref = Group.get(Group.gid == task)
                qref = gref.questiondata[0]
                if qref.user != uref:
                    return False  # not your task
                # update tag
                qref.tags = tag
                qref.save()
                log.info('Task {} tagged by user "{}": "{}"'.format(task, uname, tag))
                return True
        except Group.DoesNotExist:
            log.error("MsetTag -  task {} / user {} pair not known".format(task, uname))
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

    def MreviewQuestion(self, testNumber, questionNumber, version):
        # shift ownership to "reviewer"
        revref = User.get(name="reviewer")  # should always be there

        tref = Test.get_or_none(Test.testNumber == testNumber)
        if tref is None:
            return [False]
        qref = QuestionData.get_or_none(
            QuestionData.test == tref,
            QuestionData.questionNumber == questionNumber,
            QuestionData.version == version,
            QuestionData.marked == True,
        )
        if qref is None:
            return [False]
        with plomdb.atomic():
            qref.user = revref
            qref.time = datetime.now()
            qref.save()
        log.info("Setting tq {}.{} for reviewer".format(testNumber, questionNumber))
        return [True]

    def MrevertTask(self, uname, task):
        uref = User.get(name=uname)  # authenticated, so not-None

        gref = Group.get_or_none(Group.gid == task)
        if gref is None:
            return [False, "NST"]  # no such task
        # from the group get the test, question and sumdata - all need cleaning.
        qref = gref.questiondata[0]
        tref = gref.test
        sref = tref.sumdata[0]
        # check user owns question and is "marked"
        if qref.user != uref or qref.status != "done" or qref.marked is False:
            return [False, "NAC"]  # nothing to do here
        # now update things
        log.info("User {} reverting task {}".format(uname, task))
        with plomdb.atomic():
            # clean up test
            tref.marked = False
            tref.totalled = False
            tref.finished = False
            tref.save()
            # clean up sum-data - no one should be totalling and marking at same time.
            # TODO = sort out the possible idiocy caused by simultaneous marking+totalling by client.
            sref.status = "todo"
            sref.sumMark = None
            sref.user = None
            sref.time = datetime.now()
            sref.summed = False
            sref.save()
            # clean off the question data - but keep user and state = "out"
            rval = [True, qref.annotatedFile, qref.plomFile, qref.commentFile]
            qref.marked = False
            qref.status = "out"
            qref.annotatedFile = None
            qref.md5sum = None
            qref.plomFile = None
            qref.commentFile = None
            qref.mark = None
            qref.markingTime = None
            qref.tags = ""
            qref.time = datetime.now()
            qref.save()
            # update user activity
            uref.lastAction = "Reverted M task {}".format(task)
            uref.lastActivity = datetime.now()
            uref.save()
        log.info("Reverting tq {}.{}".format(testNumber, questionNumber))
        return rval

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
                log.info("Nothing left on totaller to-do pile")
                return None

            log.debug("Next Totalling task = {}".format(x.test.testNumber))
            return x.test.testNumber

    def TgetDoneTasks(self, uname):
        """When a id-client logs on they request a list of papers they have already IDd.
        Send back the list."""
        uref = User.get(name=uname)  # authenticated, so not-None
        query = SumData.select().where(SumData.user == uref, SumData.status == "done")
        tList = []
        for x in query:
            tList.append([x.test.testNumber, x.status, x.sumMark])
        log.debug("Sending completed totalling tasks to {}".format(uname))
        return tList

    def TgiveTaskToClient(self, uname, testNumber):
        uref = User.get(name=uname)  # authenticated, so not-None
        try:
            with plomdb.atomic():
                tref = Test.get_or_none(Test.testNumber == testNumber)
                if tref.scanned == False:
                    return [False]
                sref = tref.sumdata[0]
                if sref.user is None or sref.user == uref:
                    pass
                else:  # has been claimed by someone else.
                    return [False]
                # update status, Student-number, name, id-time.
                sref.status = "out"
                sref.user = uref
                sref.time = datetime.now()
                sref.save()
                # update user activity
                uref.lastAction = "Took T task {}".format(testNumber)
                uref.lastActivity = datetime.now()
                uref.save()
                # return [true, page1]
                pref = Page.get(Page.test == tref, Page.pageNumber == 1)
                return [True, pref.fileName]
                log.info(
                    "Giving totalling task {} to user {}".format(testNumber, uname)
                )
                return rval

        except Test.DoesNotExist:
            log.warning(
                "Cannot give totalling task {} to {} - task not known".format(
                    testNumber, uname
                )
            )
            return False

    def TdidNotFinish(self, uname, testNumber):
        """When user logs off, any images they have still out should be put
        back on todo pile
        """
        uref = User.get(name=uname)  # authenticated, so not-None
        # Log user returning given tgv.
        try:
            with plomdb.atomic():
                tref = Test.get_or_none(Test.testNumber == testNumber)
                if tref.scanned == False:
                    return
                sref = tref.sumdata[0]
                if sref.user == uref and sref.status == "out":
                    pass
                else:  # has been claimed by someone else.
                    return
                # update status, Student-number, name, id-time.
                sref.status = "todo"
                sref.user = None
                sref.time = datetime.now()
                sref.summed = False
                sref.save()
                tref.summed = False
                tref.save()
                log.info("User {} did not total task {}".format(uname, testNumber))
        except Test.DoesNotExist:
            log.error("TdidNotFinish - test number {} not known".format(testNumber))
            return False

    def TgetImage(self, uname, t):
        uref = User.get(name=uname)  # authenticated, so not-None
        tref = Test.get_or_none(Test.testNumber == t)
        if tref.scanned == False:
            return [False]
        sref = tref.sumdata[0]
        # check if task given to user or user=manager
        if sref.user == uref or uname == "manager":
            pass
        else:
            return [False]
        pref = Page.get(Page.test == tref, Page.pageNumber == 1)
        log.info(
            "Sending cover-page of test {} to user {} = {}".format(
                t, uname, pref.fileName
            )
        )
        return [True, pref.fileName]

    def TtakeTaskFromClient(self, testNumber, uname, totalMark):
        uref = User.get(name=uname)  # authenticated, so not-None

        try:
            with plomdb.atomic():
                tref = Test.get_or_none(Test.testNumber == testNumber)
                if tref.scanned == False:
                    return [False]
                sref = tref.sumdata[0]
                if sref.user != uref:
                    # that belongs to someone else - this is a serious error
                    log.error(
                        'User "{}" returned totalled-task {} that belongs to "{}"'.format(
                            uname, testNumber, sref.user.name
                        )
                    )
                    return [False]
                # update status, Student-number, name, id-time.
                sref.status = "done"
                sref.sumMark = totalMark
                sref.summed = True
                sref.time = datetime.now()
                sref.save()
                tref.totalled = True
                tref.save()
                # update user activity
                uref.lastAction = "Returned T task {}".format(testNumber)
                uref.lastActivity = datetime.now()
                uref.save()
                log.debug(
                    "User {} returning totalled-task {} with {}".format(
                        uname, testNumber, totalMark
                    )
                )
                return [True]
        except Test.DoesNotExist:
            log.error(
                "TtakeTaskFromClient - test number {} not known".format(testNumber)
            )
            return [False]
