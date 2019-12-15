from peewee import *

plomdb = SqliteDatabase("plom.db")

# the test contains groups
# test bools something like
# produced = we've built the PDF
# scanned = we've fed it to students, scanned it into system.
# identified = ID-ing is done
# marked = marking is done
# finished = we've rebuilt the PDF at the end with coverpages etc etc


class Test(Model):
    testNumber = IntegerField(primary_key=True, unique=True)
    studentID = CharField(unique=True, null=True)
    studentName = CharField(null=True)
    totalMark = IntegerField(null=True)
    # some state bools
    produced = BooleanField(default=False)
    scanned = BooleanField(default=False)
    identified = BooleanField(default=False)
    marked = BooleanField(default=False)
    finished = BooleanField(default=False)

    class Meta:
        database = plomdb


# group knows its test
# group status will evolve something like... [todo, outwithclient, done]
class Group(Model):
    test = ForeignKeyField(Test, backref="groups")
    gid = CharField(unique=True)  # must be unique
    groupType = CharField()  # to distinguish between ID, DNM, and Mark groups
    status = CharField(default="")
    version = IntegerField(default=1)
    # flags
    scanned = BooleanField(default=False)

    class Meta:
        database = plomdb


# Data for question-groupsWe have the CPU time.We have the CPU time.
class MarkData(Model):
    gid = ForeignKeyField(Group, backref="markdata")
    groupNumber = IntegerField(null=False)
    version = IntegerField(null=False)
    annotatedFile = CharField(null=True)
    mark = IntegerField(null=True)
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

    class Meta:
        database = plomdb


# Duplicate pages should be attached to the page their are duplicating
# When duplication status resolved we can move them about.
class DuplicatePages(Model):
    page = ForeignKeyField(Page, backref="duplicates")
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
                    MarkData,
                    Page,
                    UnknownPages,
                    DuplicatePages,
                    DiscardedPages,
                ]
            )

    def createTest(self, t):
        try:
            Test.create(testNumber=t)  # must be unique
        except IntegrityError as e:
            print("Test {} already exists.".format(t))
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
                    print("Page {} for test {} already exists.".format(p, t))
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
            gref = Group.create(
                test=tref, gid=gid, groupType="i", version=1
            )  # must be unique
        except IntegrityError as e:
            print("Group {} of Test {} already exists.".format(gid, t))
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
            gref = Group.create(
                test=tref, gid=gid, groupType="d", version=1
            )  # must be unique
        except IntegrityError as e:
            print("Group {} of Test {} already exists.".format(gid, t))
            return False
        return self.addPages(tref, gref, t, pages, 1)

    def createMGroup(self, t, g, v, pages):
        tref = Test.get_or_none(testNumber=t)
        if tref is None:
            print("No test with number {}".format(t))
            return False

        gid = "m{}g{}".format(str(t).zfill(4), g)
        # make the mgroup
        try:
            gref = Group.create(
                test=tref, gid=gid, groupType="m", version=v
            )  # must be unique
        except IntegrityError as e:
            print("Question {} of Test {} already exists.".format(gid, t))
            return False
        try:
            mref = MarkData.create(gid=gref, groupNumber=g, version=v)
        except IntegrityError as e:
            print("Markdata {} of question {} already exists.".format(mref, gid))
            return False
        return self.addPages(tref, gref, t, pages, v)

    def printGroups(self, t):
        tref = Test.get_or_none(testNumber=t)
        if tref is None:
            return
        for x in tref.groups:
            if x.groupType == "m":
                mdata = x.markdata[0]
                print(
                    x.gid,
                    x.groupType,
                    x.status,
                    mdata.groupNumber,
                    mdata.version,
                    mdata.mark,
                    mdata.annotatedFile,
                )
            else:
                print(x.gid, x.groupType)
            for p in x.pages:
                print("\t", p.pageNumber, p.version)

    def printPagesByTest(self, t):
        tref = Test.get_or_none(testNumber=t)
        if tref is None:
            return
        for p in tref.pages:
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
        with plomdb.atomic():
            for g in tref.groups:
                if g.groupType == "i":
                    g.status = "identified"
                    g.save()
                    break
            tref.studentID = sid
            tref.studentName = sname
            tref.identified = True
            tref.save()

    def uploadKnownPage(self, t, p, v, oname, nname, md5):
        tref = Test.get_or_none(testNumber=t)
        if tref is None:
            return [False, "Cannot find test"]
        pref = Page.get_or_none(test=tref, pageNumber=p, version=v)
        if pref is None:
            return [False, "Cannot find page,version"]
        if pref.scanned:
            # have already loaded an image for this page - so this is actually a duplicate
            print("This appears to be a duplicate. Checking md5sums")
            if md5 == pref.md5sum:
                # Exact duplicate - md5sum of this image is sames as the one already in database
                return [False, "Exact duplicate of page already in database"]
            # deal with duplicate page
            return [True, "Is duplicate of {} {} {}".format(t, p, v)]
        else:
            with plomdb.atomic():
                pref.originalName = oname
                pref.fileName = nname
                pref.md5sum = md5
                pref.scanned = True
                pref.save()
                return [True, pref.pid]
