from datetime import datetime
from peewee import *
import logging
import json
from collections import defaultdict

markdb = SqliteDatabase('../resources/test_marks.db')


class GroupImage(Model):
    tgv = CharField(unique=True)
    originalFile = CharField(unique=True)

    number = IntegerField()
    pageGroup = IntegerField()
    version = IntegerField()
    annotatedFile = CharField()
    status = CharField()
    user = CharField()
    time = DateTimeField()
    mark = IntegerField()
    markingTime = IntegerField()

    class Meta:
        database = markdb


class MarkDatabase:
    def __init__(self):
        logging.basicConfig(filename='test_mark_storage.log', filemode='w', level=logging.INFO, format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')
        logging.info("Initialised ")
        self.createTable()

    def connectToDB(self):
        logging.info("Connecting to database")
        with markdb:
            markdb.connect()

    def createTable(self):
        logging.info("Creating database tables")
        with markdb:
            markdb.create_tables([GroupImage])

    def shutdown(self):
        with markdb:
            markdb.close()

    def clean(self):
        logging.info("Cleaning out database")
        query = GroupImage.delete()
        query.execute()

    def printGroupImageWithCode(self, code):
        query = GroupImage.select().where(GroupImage.tgz == code).order_by(GroupImage.tgv)
        for x in query:
            print(x.tgv, x.status, x.user, x.time, x.mark, x.markingTime)

    def printToDo(self):
        query = GroupImage.select().where(GroupImage.status == 'ToDo').order_by(GroupImage.tgv)
        for x in query:
            print(x.tgv, x.status)

    def printOutForMarking(self):
        query = GroupImage.select().where(GroupImage.status == 'OutForMarking').order_by(GroupImage.tgv)
        for x in query:
            print(x.tgv, x.status, x.user, x.time)

    def printMarked(self):
        query = GroupImage.select().where(GroupImage.status == 'Marked').order_by(GroupImage.tgv)
        for x in query:
            print(x.tgv, x.status, x.user, x.time, x.mark, x.markingTime)

    def printAllGroupImages(self):
        self.printToDo()
        self.printOutForMarking()
        self.printMarked()

    def countAll(self, pg, v):
        try:
            return GroupImage.select().where(GroupImage.pageGroup == pg, GroupImage.version == v).count()
        except GroupImage.DoesNotExist:
                return 0

    def countMarked(self, pg, v):
        try:
            return GroupImage.select().where(GroupImage.pageGroup == pg, GroupImage.version == v, GroupImage.status == 'Marked').count()
        except GroupImage.DoesNotExist:
            return 0

    def addUnmarkedGroupImage(self, t, pg, v, code, fname):
        logging.info("Adding unmarked GroupImage {} at {} to database".format(code, fname))
        try:
            with markdb.atomic():
                sheet = GroupImage.create(number=t, pageGroup=pg, version=v, tgv=code, originalFile=fname, annotatedFile='', status='ToDo', user='None', time=datetime.now(), mark=-1, markingTime=0)
        except IntegrityError:
            logging.info("GroupImage {} {} already exists.".format(t, code))

    def giveGroupImageToClient(self, username, pg, v):
        try:
            with markdb.atomic():
                x = GroupImage.get(status='ToDo', pageGroup=pg, version=v)
                logging.info("Sending GroupImage {:s} to client {:s}".format(x.tgv, username))
                x.status = 'OutForMarking'
                x.user = username
                x.time = datetime.now()
                x.save()
                return (x.tgv, x.originalFile)
        except GroupImage.DoesNotExist:
            logging.info("Nothing left on To-Do pile")
            return (None, None)

    def takeGroupImageFromClient(self, code, username, mark, fname, mt):
        try:
            with markdb.atomic():
                x = GroupImage.get(tgv=code, user=username)
                x.status = 'Marked'
                x.mark = mark
                x.annotatedFile = fname
                x.time = datetime.now()
                x.markingTime = mt
                x.save()
                logging.info("GroupImage {} marked {} by user {} and placed at {}".format(code, mark, username, fname))
        except GroupImage.DoesNotExist:
            self.printGroupImageWithCode(code)
            logging.info("That GroupImage number {} / username {} pair not known".format(code, username))

    def didntFinish(self, username, code):
        logging.info("User {:s} returning unmarked GroupImage {}".format(username, code))
        with markdb.atomic():
            query = GroupImage.select().where(GroupImage.user == username, GroupImage.tgv == code)
            for x in query:
                x.status = 'ToDo'
                x.user = 'None'
                x.time = datetime.now()
                x.markingTime = 0
                x.save()
                logging.info(">>> Returning GroupImage {:s} from user {:s}".format(x.tgv, username))

    def saveMarked(self):
        GroupImagesMarked = defaultdict(lambda: defaultdict(list))
        query = GroupImage.select().where(GroupImage.status == 'Marked').order_by(GroupImage.tgv)
        for x in query:
            GroupImagesMarked[x.number][x.pageGroup] = [x.version, x.mark, x.user]
        eg = open("../resources/groupImagesMarked.json", 'w')
        eg.write(json.dumps(GroupImagesMarked, indent=2, sort_keys=True))
        eg.close()

    def resetUsersToDo(self, username):
        logging.info("Anything from user {} that is OutForMarking - reset it as ToDo.".format(username))
        query = GroupImage.select().where(GroupImage.user == username, GroupImage.status == "OutForMarking")
        for x in query:
            x.status = 'ToDo'
            x.user = 'None'
            x.time = datetime.now()
            x.markingTime = 0
            x.save()
            logging.info(">>> Returning GroupImage {} from {} to the ToDo pile".format(x.tgv, username))
