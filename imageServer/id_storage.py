__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2018 Andrew Rechnitzer"
__credits__ = ["Andrew Rechnitzer", "Colin MacDonald", "Elvis Cai"]
__license__ = "GPLv3"

from datetime import datetime
from peewee import *
import logging
import json


# open the database file in resources.
iddb = SqliteDatabase("../resources/identity.db")


class IDImage(Model):
    """Simple database model for peewee."""

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
    """Class to handle all our database transactions."""

    def __init__(self, logger):
        """Fire up basic logging and create the table in the database."""
        self.logging = logger
        self.logging.info("Initialised ")
        self.createTable()

    def connectToDB(self):
        """Connect to the database"""
        self.logging.info("Connecting to database")
        with iddb:
            iddb.connect()

    def createTable(self):
        """Create the required table in the database"""
        self.logging.info("Creating database tables")
        with iddb:
            iddb.create_tables([IDImage])

    def shutdown(self):
        """Shut connection to the database"""
        with iddb:
            iddb.close()

    def printToDo(self):
        """Print every record that is still ToDo"""
        query = (
            IDImage.select().where(IDImage.status == "ToDo").order_by(IDImage.number)
        )
        for x in query:
            print(x.number, x.tgv, x.status)

    def printOutForIDing(self):
        """Print every record that is out for ID-ing"""
        query = (
            IDImage.select()
            .where(IDImage.status == "OutForIDing")
            .order_by(IDImage.number)
        )
        for x in query:
            print(x.number, x.tgv, x.status, x.user, x.time)

    def printIdentified(self):
        """Print every record that has been ID'd"""
        query = (
            IDImage.select()
            .where(IDImage.status == "Identified")
            .order_by(IDImage.number)
        )
        for x in query:
            print(x.number, x.tgv, x.status, x.user, x.time, x.sid, x.sname)

    def printAllIDImages(self):
        """Print all the records"""
        self.printToDo()
        self.printOutForIDing()
        self.printIdentified()

    def countAll(self):
        """Count all the records"""
        try:
            return IDImage.select().count()
        except IDImage.DoesNotExist:
            return 0

    def countIdentified(self):
        """Count all the ID'd records"""
        try:
            return IDImage.select().where(IDImage.status == "Identified").count()
        except IDImage.DoesNotExist:
            return 0

    def addUnIDdExam(self, t, code):
        """Add exam number t with given code to the database"""
        self.logging.info("Adding unid'd IDImage {} to database".format(t))
        try:
            with iddb.atomic():
                IDImage.create(
                    number=t,
                    tgv=code,
                    status="ToDo",
                    user="None",
                    time=datetime.now(),
                    sid=-t,
                    sname="",
                )
        except IntegrityError:
            self.logging.info("IDImage {} {} already exists.".format(t, code))

    def giveIDImageToClient(self, username):
        """Find unid'd test and send to client"""
        try:
            with iddb.atomic():
                # Grab image from todo pile
                x = IDImage.get(status="ToDo")
                # log it.
                self.logging.info(
                    "Passing IDImage {} {} to client {}".format(
                        x.number, x.tgv, username
                    )
                )
                # Update status, user, time.
                x.status = "OutForIDing"
                x.user = username
                x.time = datetime.now()
                x.save()
                # return tgv.
                return x.tgv
        except IDImage.DoesNotExist:
            self.logging.info("Nothing left on To-Do pile")

    def takeIDImageFromClient(self, code, username, sid, sname):
        """Get ID'dimage back from client - update record in database."""
        try:
            with iddb.atomic():
                # get the record by code + username.
                x = IDImage.get(tgv=code, user=username)
                # update status, Student-number, name, id-time.
                x.status = "Identified"
                x.sid = sid
                x.sname = sname
                x.time = datetime.now()
                x.save()
                # log it.
                self.logging.info(
                    "IDImage {} {} identified as {} {} by user {}".format(
                        x.number, code, sid, sname, username
                    )
                )
                return True
        except IntegrityError:
            self.logging.info("Student number {} already entered".format(sid))
            return False
        except IDImage.DoesNotExist:
            self.logging.info(
                "That IDImage number {} / username {} pair not known".format(
                    code, username
                )
            )
            return False

    def didntFinish(self, username, code):
        """When user logs off, any images they have still out should be put
        back on todo pile
        """
        # Log user returning given tgv.
        self.logging.info("User {} returning unid'd IDImages {}".format(username, code))
        with iddb.atomic():
            # get the record by username+code
            query = IDImage.select().where(
                IDImage.user == username, IDImage.tgv == code
            )
            for x in query:
                # set it back as todo, no user, update time and save.
                x.status = "ToDo"
                x.user = "None"
                x.time = datetime.now()
                x.save()
                # log the result.
                self.logging.info(
                    ">>> Returning IDImage {} {} from user {}".format(
                        x.number, x.tgv, username
                    )
                )

    def saveIdentified(self):
        """Dump all the ID'd tests to a json."""
        examsIdentified = {}
        query = (
            IDImage.select()
            .where(IDImage.status == "Identified")
            .order_by(IDImage.number)
        )
        for x in query:
            examsIdentified[x.number] = [x.tgv, x.sid, x.sname, x.user]
        eg = open("../resources/examsIdentified.json", "w")
        eg.write(json.dumps(examsIdentified, indent=2, sort_keys=True))
        eg.close()

    def resetUsersToDo(self, username):
        """Take anything currently out with user and put it back
        on the todo pile
        """
        self.logging.info(
            "Anything from user {} that is OutForIDing - reset it as ToDo.".format(
                username
            )
        )
        query = IDImage.select().where(
            IDImage.user == username, IDImage.status == "OutForIDing"
        )
        for x in query:
            x.status = "ToDo"
            x.user = "None"
            x.time = datetime.now()
            x.save()
            self.logging.info(
                ">>> Returning IDImage {} from {} to the ToDo pile".format(
                    x.tgv, username
                )
            )
