from datetime import datetime
from peewee import *
import logging
import json


iddb = SqliteDatabase('../resources/identity.db')


class IDImage(Model):
    number = IntegerField(unique=True)
    tgv = CharField()
    status = CharField()
    user = CharField()
    time = DateTimeField()
    sid = CharField(unique=True)
    sname = CharField()

    class Meta:
        database = iddb


class IDDatabase:
    def __init__(self):
        logging.basicConfig(filename='identity_storage.log', filemode='w', level=logging.INFO, format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')
        logging.info("Initialised ")
        self.createTable()

    def connectToDB(self):
        logging.info("Connecting to database")
        with iddb:
            iddb.connect()

    def createTable(self):
        logging.info("Creating database tables")
        with iddb:
            iddb.create_tables([IDImage])

    def shutdown(self):
        with iddb:
            iddb.close()

    def clean(self):
        logging.info("Cleaning out database")
        query = IDImage.delete()
        query.execute()

    def printToDo(self):
        query = IDImage.select().where(IDImage.status == 'ToDo').order_by(IDImage.number)
        for x in query:
            print(x.number, x.tgv, x.status)

    def printOutForIDing(self):
        query = IDImage.select().where(IDImage.status == 'OutForIDing').order_by(IDImage.number)
        for x in query:
            print(x.number, x.tgv, x.status, x.user, x.time)

    def printIdentified(self):
        query = IDImage.select().where(IDImage.status == 'Identified').order_by(IDImage.number)
        for x in query:
            print(x.number, x.tgv, x.status, x.user, x.time, x.sid, x.sname)

    def printAllIDImages(self):
        self.printToDo()
        self.printOutForIDing()
        self.printIdentified()

    def countAll(self):
        try:
            return IDImage.select().count()
        except IDImage.DoesNotExist:
            return 0

    def countIdentified(self):
        try:
            return IDImage.select().where(IDImage.status == 'Identified').count()
        except IDImage.DoesNotExist:
            return 0

    def addUnIDdExam(self, t, code):
        logging.info("Adding unid'd IDImage {} to database".format(t))
        try:
            with iddb.atomic():
                sheet = IDImage.create(number=t, tgv=code, status='ToDo', user='None', time=datetime.now(), sid=-t, sname="")
        except IntegrityError:
            logging.info("IDImage {} {} already exists.".format(t, code))

    def giveIDImageToClient(self, username):
        try:
            with iddb.atomic():
                x = IDImage.get(status='ToDo')
                logging.info("Passing IDImage {:d} {:s} to client {:s}".format(x.number, x.tgv, username))
                x.status = 'OutForIDing'
                x.user = username
                x.time = datetime.now()
                x.save()
                return x.tgv
        except IDImage.DoesNotExist:
            logging.info("Nothing left on To-Do pile")

    def takeIDImageFromClient(self, code, username, sid, sname):
        try:
            with iddb.atomic():
                x = IDImage.get(tgv=code, user=username)
                x.status = 'Identified'
                x.sid = sid
                x.sname = sname
                x.time = datetime.now()
                x.save()
                logging.info("IDImage {:d} {:s} identified as {:s} {:s} by user {:s}".format(x.number, code, sid, sname, username))
                return True
        except IntegrityError:
            logging.info("Student number {} already entered".format(sid))
            return(False)
        except IDImage.DoesNotExist:
            logging.info("That IDImage number / username pair not known")
            return(False)

    def didntFinish(self, username, code):
        logging.info("User {} returning unid'd IDImages {}".format(username, code))
        with iddb.atomic():
            query = IDImage.select().where(IDImage.user == username, IDImage.tgv == code)
            for x in query:
                x.status = 'ToDo'
                x.user = 'None'
                x.time = datetime.now()
                x.save()
                logging.info(">>> Returning IDImage {:d} {:s} from user {:s}".format(x.number, x.tgv, username))

    def saveIdentified(self):
        examsIdentified = {}
        query = IDImage.select().where(IDImage.status == 'Identified').order_by(IDImage.number)
        for x in query:
            examsIdentified[x.number] = [x.tgv, x.sid, x.sname, x.user]
        eg = open("../resources/examsIdentified.json", 'w')
        eg.write(json.dumps(examsIdentified, indent=2, sort_keys=True))
        eg.close()

    def resetUsersToDo(self, username):
        logging.info("Anything from user {} that is OutForIDing - reset it as ToDo.".format(username))
        query = IDImage.select().where(IDImage.user == username, IDImage.status == "OutForIDing")
        for x in query:
            x.status = 'ToDo'
            x.user = 'None'
            x.time = datetime.now()
            x.save()
            logging.info(">>> Returning IDImage {} from {} to the ToDo pile".format(x.tgv, username))
