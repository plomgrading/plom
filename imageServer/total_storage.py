__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2018-2019 Andrew Rechnitzer"
__credits__ = ["Andrew Rechnitzer"]
__license__ = "AGPLv3"

from datetime import datetime
from peewee import *
import logging
import json


# open the database file in resources.
tdb = SqliteDatabase("../resources/totals.db")


class TotalImage(Model):
    """Simple database model for peewee."""

    number = IntegerField(unique=True)
    tgv = CharField()
    status = CharField()
    user = CharField()
    time = DateTimeField()
    mark = IntegerField()

    class Meta:
        database = tdb


class TotalDatabase:
    """Class to handle all our database transactions."""

    def __init__(self, logger):
        """Fire up basic logging and create the table in the database."""
        self.logging = logger
        self.logging.info("Initialised ")
        self.createTable()

    def connectToDB(self):
        """Connect to the database"""
        self.logging.info("Connecting to database")
        with tdb:
            tdb.connect()

    def createTable(self):
        """Create the required table in the database"""
        self.logging.info("Creating database tables")
        with tdb:
            tdb.create_tables([TotalImage])

    def shutdown(self):
        """Shut connection to the database"""
        with tdb:
            tdb.close()

    def printToDo(self):
        """Print every record that is still ToDo"""
        query = (
            TotalImage.select()
            .where(TotalImage.status == "ToDo")
            .order_by(TotalImage.number)
        )
        for x in query:
            print(x.number, x.tgv, x.status)

    def printOutForTotaling(self):
        """Print every record that is out for totaling"""
        query = (
            TotalImage.select()
            .where(TotalImage.status == "OutForTotaling")
            .order_by(TotalImage.number)
        )
        for x in query:
            print(x.number, x.tgv, x.status, x.user, x.time)

    def printTotaled(self):
        """Print every record that has been totaled"""
        query = (
            TotalImage.select()
            .where(TotalImage.status == "Totaled")
            .order_by(TotalImage.number)
        )
        for x in query:
            print(x.number, x.tgv, x.status, x.user, x.time, x.mark)

    def printAllTotalImages(self):
        """Print all the records"""
        self.printToDo()
        self.printOutForTotaling()
        self.printIdentified()

    def countAll(self):
        """Count all the records"""
        try:
            return TotalImage.select().count()
        except TotalImage.DoesNotExist:
            return 0

    def countTotaled(self):
        """Count all the totaled records"""
        try:
            return TotalImage.select().where(TotalImage.status == "Totaled").count()
        except TotalImage.DoesNotExist:
            return 0

    def addUntotaledExam(self, t, code):
        """Add exam number t with given code to the database"""
        self.logging.info("Adding unid'd TotalImage {} to database".format(t))
        try:
            with tdb.atomic():
                TotalImage.create(
                    number=t,
                    tgv=code,
                    status="ToDo",
                    user="None",
                    time=datetime.now(),
                    mark=-1,
                )
        except IntegrityError:
            self.logging.info("TotalImage {} {} already exists.".format(t, code))

    def giveTotalImageToClient(self, username):
        """Find unid'd test and send to client"""
        try:
            with tdb.atomic():
                # Grab image from todo pile
                x = TotalImage.get(status="ToDo")
                # log it.
                self.logging.info(
                    "Passing TotalImage {} {} to client {}".format(
                        x.number, x.tgv, username
                    )
                )
                # Update status, user, time.
                x.status = "OutForTotaling"
                x.user = username
                x.time = datetime.now()
                x.save()
                # return tgv.
                return x.tgv
        except TotalImage.DoesNotExist:
            self.logging.info("Nothing left on To-Do pile")

    def takeTotalImageFromClient(self, code, username, value):
        """Get ID'dimage back from client - update record in database."""
        try:
            with tdb.atomic():
                # get the record by code + username.
                x = TotalImage.get(tgv=code, user=username)
                # update status, Student-number, name, id-time.
                x.status = "Totaled"
                x.mark = value
                x.save()
                # log it.
                self.logging.info(
                    "TotalImage {} {} totaled as {} by user {}".format(
                        x.number, code, value, username
                    )
                )
                return True

        except TotalImage.DoesNotExist:
            self.logging.info(
                "That TotalImage number {} / username {} pair not known".format(
                    code, username
                )
            )
            return False

    def didntFinish(self, username, code):
        """When user logs off, any images they have still out should be put
        back on todo pile
        """
        # Log user returning given tgv.
        self.logging.info(
            "User {} returning untotaled TotalImages {}".format(username, code)
        )
        with tdb.atomic():
            # get the record by username+code
            query = TotalImage.select().where(
                TotalImage.user == username, TotalImage.tgv == code
            )
            for x in query:
                # set it back as todo, no user, update time and save.
                x.status = "ToDo"
                x.user = "None"
                x.time = datetime.now()
                x.save()
                # log the result.
                self.logging.info(
                    ">>> Returning TotalImage {} {} from user {}".format(
                        x.number, x.tgv, username
                    )
                )

    def saveTotaled(self):
        """Dump all the ID'd tests to a json."""
        examsTotaled = {}
        query = (
            TotalImage.select()
            .where(TotalImage.status == "Totaled")
            .order_by(TotalImage.number)
        )
        for x in query:
            examsTotaled[x.number] = [x.tgv, x.mark, x.user]
        eg = open("../resources/examsTotaled.json", "w")
        eg.write(json.dumps(examsTotaled, indent=2, sort_keys=True))
        eg.close()

    def resetUsersToDo(self, username):
        """Take anything currently out with user and put it back
        on the todo pile
        """
        self.logging.info(
            "Anything from user {} that is OutForTotaling - reset it as ToDo.".format(
                username
            )
        )
        query = TotalImage.select().where(
            TotalImage.user == username, TotalImage.status == "OutForTotaling"
        )
        for x in query:
            x.status = "ToDo"
            x.user = "None"
            x.time = datetime.now()
            x.save()
            self.logging.info(
                ">>> Returning TotalImage {} from {} to the ToDo pile".format(
                    x.tgv, username
                )
            )

    def buildTotalList(self, username):
        query = TotalImage.select().where(TotalImage.user == username)
        tList = []
        for x in query:
            if x.status == "Totaled":
                tList.append([x.tgv, x.status, x.mark])
        return tList

    def getGroupImage(self, username, code):
        try:
            with tdb.atomic():
                x = TotalImage.get(tgv=code, user=username)
                return x.tgv
        except TotalImage.DoesNotExist:
            print("Request for non-existant tgv = {}".format(code))
            return None

    def checkExists(self, code):
        try:
            with tdb.atomic():
                x = TotalImage.get(tgv=code)
                return True
        except TotalImage.DoesNotExist:
            return False
