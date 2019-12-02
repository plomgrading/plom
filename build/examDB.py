from peewee import *

plomdb = SqliteDatabase("plom.db")

# the test contains groups
class Test(Model):
    testNumber = IntegerField(unique=True, primary_key=True)
    status = CharField()
    studentID = CharField(unique=True, null=True)
    studentName = CharField(null=True)
    totalMark = IntegerField(null=True)

    class Meta:
        database = plomdb


# groups contain pages
class Group(Model):
    test = ForeignKeyField(Test, backref="groups")
    groupNumber = IntegerField(null=False)  # use 0 for IDGroup, -1 for DNW group?
    gid = CharField(unique=True)  # must be unique
    status = CharField()
    version = IntegerField(default=1)
    annotatedFile = CharField(null=True)
    mark = IntegerField(null=True)

    class Meta:
        database = plomdb


class Page(Model):
    test = ForeignKeyField(Test, backref="pages")
    group = ForeignKeyField(Group, backref="pages")
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
            plomdb.create_tables([Test, Group, Page])

    def addTest(self, t):
        try:
            with plomdb.atomic():
                Test.create(testNumber=t, status="produced")  # must be unique
        except IntegrityError as e:
            print("Test {} already exists.".format(t))
            print(e)

    def addIDGroup(self, t, idPages):
        gid = "id{}".format(str(t).zfill(4))

        # a ref to the test
        tref = Test.get(testNumber=t)
        try:
            with plomdb.atomic():
                # create the group and keep a ref to it
                gref = Group.create(
                    test=tref, groupNumber="0", gid=gid, status="produced"
                )
        except IntegrityError as e:
            print("IDGroup for test {} already exists.".format(t))
            print(e)

        print("Added test {} group {}".format(tref, gref))
        print("Now need to add pages {}".format(idPages))
        for p in idPages:
            try:
                with plomdb.atomic():
                    Page.create(
                        test=tref,
                        group=gref,
                        status="produced",
                        pageNumber=p,
                        version=1,
                        pid="{}.{}".format(t, p),
                        originalFile="",
                    )
            except IntegrityError as e:
                print("Page {} for test {} already exists.".format(p, t))
                print(e)

    def addDNMGroup(self, t, dnmPages):
        gid = "dnm{}".format(str(t).zfill(4))

        # a ref to the test
        tref = Test.get(testNumber=t)
        try:
            with plomdb.atomic():
                # create the group and keep a ref to it
                gref = Group.create(
                    test=tref, groupNumber="-1", gid=gid, status="produced"
                )
        except IntegrityError as e:
            print("DNMGroup for test {} already exists.".format(t))
            print(e)

        print("Added test {} group {}".format(tref, gref))
        print("Now need to add pages {}".format(dnmPages))
        for p in dnmPages:
            try:
                with plomdb.atomic():
                    Page.create(
                        test=tref,
                        group=gref,
                        status="produced",
                        pageNumber=p,
                        version=1,
                        pid="{}.{}".format(t, p),
                        originalFile="",
                    )
            except IntegrityError as e:
                print("Page {} for test {} already exists.".format(p, t))
                print(e)
