__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2018-2019 Andrew Rechnitzer"
__credits__ = ["Andrew Rechnitzer", "Colin Macdonald", "Elvis Cai"]
__license__ = "AGPLv3"

from collections import defaultdict
from datetime import datetime
import json
import logging
from peewee import *


# open the database file in resources.
markdb = SqliteDatabase("../resources/test_marks.db")


class GroupImage(Model):
    """Simple database model for peewee."""

    tgv = CharField(unique=True)
    originalFile = CharField(unique=True)
    number = IntegerField()
    pageGroup = IntegerField()
    version = IntegerField()
    annotatedFile = CharField()
    plomFile = CharField()
    commentFile = CharField()
    status = CharField()
    user = CharField()
    time = DateTimeField()
    mark = IntegerField()
    markingTime = IntegerField()
    tags = CharField()

    class Meta:
        database = markdb


class MarkDatabase:
    """Class to handle all our database transactions."""

    def __init__(self, logger):
        """Fire up basic logging and create the table in the database."""
        self.logging = logger
        self.logging.info("Initialised ")
        self.createTable()

    def connectToDB(self):
        """Connect to the database"""
        self.logging.info("Connecting to database")
        with markdb:
            markdb.connect()

    def createTable(self):
        """Create the required table in the database"""
        self.logging.info("Creating database tables")
        with markdb:
            markdb.create_tables([GroupImage])

    def shutdown(self):
        """Shut connection to the database"""
        with markdb:
            markdb.close()

    def printGroupImageWithCode(self, code):
        """Print every record with given code"""
        query = (
            GroupImage.select().where(GroupImage.tgv == code).order_by(GroupImage.tgv)
        )
        for x in query:
            print(x.tgv, x.status, x.user, x.time, x.mark, x.markingTime, x.tags)

    def printToDo(self):
        """Print every record that is still ToDo"""
        query = (
            GroupImage.select()
            .where(GroupImage.status == "ToDo")
            .order_by(GroupImage.tgv)
        )
        for x in query:
            print(x.tgv, x.status)

    def printOutForMarking(self):
        """Print every record that is out for marking"""
        query = (
            GroupImage.select()
            .where(GroupImage.status == "OutForMarking")
            .order_by(GroupImage.tgv)
        )
        for x in query:
            print(x.tgv, x.status, x.user, x.time)

    def printMarked(self):
        """Print every record that has been marked"""
        query = (
            GroupImage.select()
            .where(GroupImage.status == "Marked")
            .order_by(GroupImage.tgv)
        )
        for x in query:
            print(x.tgv, x.status, x.user, x.time, x.mark, x.markingTime, x.tags)

    def printAllGroupImages(self):
        """Print all records"""
        self.printToDo()
        self.printOutForMarking()
        self.printMarked()

    def countAll(self, pg, v):
        """Count all records in given (group,version)"""
        try:
            return (
                GroupImage.select()
                .where(GroupImage.pageGroup == pg, GroupImage.version == v)
                .count()
            )
        except GroupImage.DoesNotExist:
            return 0

    def countMarked(self, pg, v):
        """Count all records in given (group,version) that have been marked"""
        try:
            return (
                GroupImage.select()
                .where(
                    GroupImage.pageGroup == pg,
                    GroupImage.version == v,
                    GroupImage.status == "Marked",
                )
                .count()
            )
        except GroupImage.DoesNotExist:
            return 0

    def addUnmarkedGroupImage(self, t, pg, v, code, fname):
        """Add a pageimage with given number, group, version, code
        and filename.
        """
        self.logging.info(
            "Adding unmarked GroupImage {} at {} to database".format(code, fname)
        )
        try:
            with markdb.atomic():
                GroupImage.create(
                    number=t,
                    pageGroup=pg,
                    version=v,
                    tgv=code,
                    originalFile=fname,
                    annotatedFile="",
                    plomFile="",
                    commentFile="",
                    status="ToDo",
                    user="None",
                    time=datetime.now(),
                    mark=-1,
                    markingTime=0,
                    tags="",
                )
        except IntegrityError:
            self.logging.info("GroupImage {} {} already exists.".format(t, code))

    def giveGroupImageToClient(self, username, pg, v):
        """Find unmarked image with (group,version) and give to client"""
        try:
            with markdb.atomic():
                # grab image from ToDo pile with required group,version
                x = GroupImage.get(status="ToDo", pageGroup=pg, version=v)
                # log it
                self.logging.info(
                    "Sending GroupImage {:s} to client {:s}".format(x.tgv, username)
                )
                # update status, user, time
                x.status = "OutForMarking"
                x.user = username
                x.time = datetime.now()
                x.save()
                # return the tgv and filename
                return (x.tgv, x.originalFile, x.tags)
        except GroupImage.DoesNotExist:
            self.logging.info("Nothing left on To-Do pile")
            return (None, None)

    def takeGroupImageFromClient(
        self, code, username, mark, fname, pname, cname, mt, tag
    ):
        """Get marked image back from client and update the record
        in the database.
        """
        try:
            with markdb.atomic():
                # get the record by code and username
                x = GroupImage.get(tgv=code, user=username)
                # update status, mark, annotate-file-name, time, and
                # time spent marking the image
                x.status = "Marked"
                x.mark = mark
                x.annotatedFile = fname
                x.plomFile = pname
                x.commentFile = cname
                x.time = datetime.now()
                x.markingTime = mt
                x.tags = tag
                x.save()
                self.logging.info(
                    "GroupImage {} marked {} by user {} and placed at {}".format(
                        code, mark, username, fname
                    )
                )
        except GroupImage.DoesNotExist:
            self.printGroupImageWithCode(code)
            self.logging.info(
                "That GroupImage number {} / username {} pair not known".format(
                    code, username
                )
            )

    def setTag(self, username, code, tag):
        """Get marked image back from client and update the record
        in the database.
        """
        try:
            with markdb.atomic():
                # get the record by code and username
                x = GroupImage.get(tgv=code, user=username)
                # update tag
                x.tags = tag
                x.save()
                self.logging.info(
                    "GroupImage {} tagged {} by user {}".format(code, tag, username)
                )
                return True
        except GroupImage.DoesNotExist:
            self.printGroupImageWithCode(code)
            self.logging.info(
                "That GroupImage number {} / username {} pair not known".format(
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
            "User {:s} returning unmarked GroupImage {}".format(username, code)
        )
        with markdb.atomic():
            # get the record by username+code
            query = GroupImage.select().where(
                GroupImage.user == username, GroupImage.tgv == code
            )
            for x in query:
                # set it back as todo, no user, update time and save.
                x.status = "ToDo"
                x.user = "None"
                x.time = datetime.now()
                x.markingTime = 0
                # x.tags = "" tags are not cleared
                x.save()
                self.logging.info(
                    ">>> Returning GroupImage {} from user {}".format(x.tgv, username)
                )

    def saveMarked(self):
        """Dump all the marked images to a json."""
        GroupImagesMarked = defaultdict(lambda: defaultdict(list))
        query = (
            GroupImage.select()
            .where(GroupImage.status == "Marked")
            .order_by(GroupImage.tgv)
        )
        for x in query:
            GroupImagesMarked[x.number][x.pageGroup] = [x.version, x.mark, x.user]
        eg = open("../resources/groupImagesMarked.json", "w")
        eg.write(json.dumps(GroupImagesMarked, indent=2, sort_keys=True))
        eg.close()

    def resetUsersToDo(self, username):
        """Take anything currently out with user and put it back
        on the todo pile
        """
        self.logging.info(
            "Anything from user {} that is OutForMarking - reset it as ToDo.".format(
                username
            )
        )
        query = GroupImage.select().where(
            GroupImage.user == username, GroupImage.status == "OutForMarking"
        )
        for x in query:
            x.status = "ToDo"
            x.user = "None"
            x.time = datetime.now()
            x.markingTime = 0
            # x.tags = "" # tag is not cleared
            x.save()
            self.logging.info(
                ">>> Returning GroupImage {} from {} to the ToDo pile".format(
                    x.tgv, username
                )
            )

    def buildMarkedList(self, username, pg, v):
        query = GroupImage.select().where(
            GroupImage.user == username,
            GroupImage.pageGroup == pg,
            GroupImage.version == v,
        )
        markedList = []
        for x in query:
            if x.status == "Marked":
                markedList.append([x.tgv, x.status, x.mark, x.markingTime, x.tags])
        return markedList

    def getGroupImage(self, username, code):
        try:
            with markdb.atomic():
                x = GroupImage.get(tgv=code, user=username)
                return (x.tgv, x.originalFile, x.annotatedFile)
        except GroupImage.DoesNotExist:
            print("Request for non-existant tgv={}".format(code))
            return (None, None)

    def getTestAll(self, number):
        lst = []
        query = (
            GroupImage.select()
            .where(GroupImage.number == int(number))
            .order_by(GroupImage.pageGroup)
        )
        for x in query:
            lst.append(x.originalFile)
        return lst
