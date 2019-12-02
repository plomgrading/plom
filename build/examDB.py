from peewee import *

plomdb = SqliteDatabase("plom.db")

# the test contains groups
class Test(Model):
    testNumber = IntegerField(primary_key=True, unique=True)
    status = CharField()
    studentID = CharField(unique=True, null=True)
    studentName = CharField(null=True)
    totalMark = IntegerField(null=True)

    class Meta:
        database = plomdb


# groups contain pages
class Group(Model):
    test = ForeignKeyField(Test, backref="groups")
    gid = CharField(primary_key=True, unique=True)  # must be unique
    status = CharField()
    version = IntegerField(default=1)

    class Meta:
        database = plomdb


class IDGroup(Group):
    test = ForeignKeyField(Test, backref="igroups")
    status = CharField()


class DNMGroup(Group):
    test = ForeignKeyField(Test, backref="dgroups")
    status = CharField()


class MGroup(Group):
    test = ForeignKeyField(Test, backref="mgroups")
    status = CharField()
    groupNumber = IntegerField(null=False)
    annotatedFile = CharField(null=True)
    mark = IntegerField(null=True)


class Page(Model):
    test = ForeignKeyField(Test, backref="pages")
    group = ForeignKeyField(Group, backref="pages")
    gid = CharField()
    pageNumber = IntegerField(null=False)
    pid = CharField(unique=True)  # to ensure uniqueness
    version = IntegerField(default=1)
    status = CharField()
    originalFile = CharField(null=True)

    class Meta:
        database = plomdb


class PlomDB:
    def __init__(self):
        with plomdb:
            plomdb.create_tables([Test, Group, IDGroup, DNMGroup, MGroup, Page])

    def addTest(self, t):
        try:
            with plomdb.atomic():
                Test.create(testNumber=t, status="produced")  # must be unique
        except IntegrityError as e:
            print("Test {} already exists.".format(t))
            print(e)

    def addPage(self, tref, gref, t, p, v):
        print("Adding p/v {}/{} to group {} of test {}".format(p, v, gref, tref))
        try:
            with plomdb.atomic():
                Page.create(
                    test=tref,
                    group=gref,
                    gid=gref.gid,
                    status="produced",
                    pageNumber=p,
                    version=v,
                    pid="t{}p{}".format(t, p),
                    originalFile="",
                )
        except IntegrityError as e:
            print("Page {} for test {} already exists.".format(p, t))
            print(e)

    def addIDGroup(self, t, idPages):
        gid = "i{}".format(str(t).zfill(4))

        # a ref to the test
        tref = Test.get(testNumber=t)
        try:
            with plomdb.atomic():
                # create the group and keep a ref to it
                gref = IDGroup.create(test=tref, gid=gid, status="produced")
        except IntegrityError as e:
            print("IDGroup for test {} already exists.".format(t))
            print(e)

        print("Added test {} group {}".format(tref, gref))
        for p in idPages:
            self.addPage(tref, gref, t, p, 1)

    def addDNMGroup(self, t, dnmPages):
        gid = "dnm{}".format(str(t).zfill(4))

        # a ref to the test
        tref = Test.get(testNumber=t)
        try:
            with plomdb.atomic():
                # create the group and keep a ref to it
                gref = DNMGroup.create(test=tref, gid=gid, status="produced")
        except IntegrityError as e:
            print("DNMGroup for test {} already exists.".format(t))
            print(e)
        print("Added test {} group {}".format(tref, gref))

        for p in dnmPages:
            self.addPage(tref, gref, t, p, 1)

    def addMGroup(self, t, g, v, pages):
        gid = "m{}g{}".format(str(t).zfill(4), str(g).zfill(2))
        # a ref to the test
        tref = Test.get(testNumber=t)
        try:
            with plomdb.atomic():
                # create the group and keep a ref to it
                gref = MGroup.create(
                    test=tref, gid=gid, groupNumber=g, status="produced"
                )
        except IntegrityError as e:
            print("MGroup {} for test {} already exists.".format(g, t))
            print(e)

        for p in pages:
            self.addPage(tref, gref, t, p, v)

    def printGroups(self, t):
        tref = Test.get(testNumber=t)
        for x in tref.igroups:
            print(x.gid)
            for p in x.pages:
                print("\t", p.pageNumber, p.version)
        for x in tref.dgroups:
            print(x.gid)
            for p in x.pages:
                print("\t", p.pageNumber, p.version)
        for x in tref.mgroups:
            print(x.gid)
            for p in x.pages:
                print("\t", p.pageNumber, p.version)

    def printPages(self, t):
        tref = Test.get(testNumber=t)
        for p in tref.pages:
            print(p.pageNumber, p.version, p.gid)
