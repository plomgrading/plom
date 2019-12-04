from peewee import *

plomdb = SqliteDatabase("plom.db")

# the test contains groups
# test status will evolve something like...
# [specified, produced, incomplete, scanned, done, finished]
# specified = we've run the spec and got a bunch of page/versions to turn into a pdf
# produced = we've built the PDF
# scanned = we've fed it to students, scanned it into system.
# done = client-facing processes are complete
# finished = we've rebuilt the PDF at the end with coverpages etc etc


class Test(Model):
    testNumber = IntegerField(primary_key=True, unique=True)
    status = CharField()
    studentID = CharField(
        unique=True, null=True
    )  # could potentially move into an "IDData"
    studentName = CharField(null=True)  # could potentially move into an "IDData"
    totalMark = IntegerField(null=True)

    class Meta:
        database = plomdb


# group knows its test
# group status will evolve something like...
# [specified, produced, scanned, todo, outwithclient, identified or marked]
class Group(Model):
    test = ForeignKeyField(Test, backref="groups")
    gid = CharField(primary_key=True, unique=True)  # must be unique
    groupType = CharField()  # to distinguish between ID, DNM, and Mark groups
    status = CharField()
    version = IntegerField(default=1)

    class Meta:
        database = plomdb


# Page knows its group and its test
# Page status will evolve
# [specified, produced, scanned]
class Page(Model):
    test = ForeignKeyField(Test, backref="pages")
    gid = ForeignKeyField(Group, backref="pages")
    pageNumber = IntegerField(null=False)
    pid = CharField(unique=True)  # to ensure uniqueness
    version = IntegerField(default=1)
    status = CharField()
    originalFile = CharField(null=True)

    class Meta:
        database = plomdb


# Data for question-groups
class MarkData(Model):
    gid = ForeignKeyField(Group, backref="mdata")
    groupNumber = IntegerField(null=False)
    version = IntegerField(null=False)
    annotatedFile = CharField(null=True)
    mark = IntegerField(null=True)

    class Meta:
        database = plomdb


class PlomDB:
    def __init__(self):
        with plomdb:
            plomdb.create_tables([Test, Group, MarkData, Page])

    def createTest(self, t):
        try:
            Test.create(testNumber=t, status="specified")  # must be unique
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
                        status="specified",
                        pageNumber=p,
                        version=v,
                        pid="t{}p{}".format(t, p),
                        originalFile="",
                    )
                except IntegrityError as e:
                    print("Page {} for test {} already exists.".format(p, t))
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
                test=tref, gid=gid, groupType="i", status="specified", version=1
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
                test=tref, gid=gid, groupType="d", status="specified", version=1
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
                test=tref, gid=gid, groupType="m", status="specified", version=v
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
                print(x.gid, x.groupType, x.status)
            for p in x.pages:
                print("\t", p.pageNumber, p.version, p.status)

    def printPagesByTest(self, t):
        tref = Test.get_or_none(testNumber=t)
        if tref is None:
            return
        for p in tref.pages:
            print(p.pageNumber, p.version, p.gid, p.status)

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
                tref.status = "produced"
                tref.save()
                for p in tref.pages:
                    p.status = "produced"
                    p.save()
                for g in tref.groups:
                    g.status = "produced"
                    g.save()

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
            tref.save()
