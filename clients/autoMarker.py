#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2020 Andrew Rechnitzer"
__credits__ = ["Andrew Rechnitzer", "Colin Macdonald"]
__license__ = "AGPL-3.0-or-later"
# SPDX-License-Identifier: AGPL-3.0-or-later

import argparse
import getpass
import json
import os
import random
import sys
import tempfile
import toml

from PyQt5.QtCore import Qt, QPointF, QRectF
from PyQt5.QtGui import QPainterPath, QPen
from PyQt5.QtWidgets import QApplication, QWidget


from plom_exceptions import *
import messenger
from pageview import PageView
from pagescene import PageScene

from tools import (
    CommandArrow,
    CommandArrowDouble,
    CommandBox,
    CommandCross,
    CommandDelete,
    CommandDelta,
    CommandEllipse,
    CommandHighlight,
    CommandLine,
    CommandPen,
    CommandPenArrow,
    CommandQMark,
    CommandText,
    CommandTick,
    CommandGDT,
    DeltaItem,
    TextItem,
    GroupDTItem,
)


sys.path.append("..")  # this allows us to import from ../resources
from resources.version import __version__
from resources.version import Plom_API_Version

lastTime = {}


def readLastTime():
    """Read the login + server options that were used on
    the last run of the client.
    """
    global lastTime
    # set some reasonable defaults.
    lastTime["user"] = ""
    lastTime["server"] = "localhost"
    lastTime["mport"] = "41984"
    lastTime["pg"] = 1
    lastTime["v"] = 1
    lastTime["fontSize"] = 10
    lastTime["upDown"] = "up"
    lastTime["mouse"] = "right"
    # If config file exists, use it to update the defaults
    if os.path.isfile("plomConfig.toml"):
        with open("plomConfig.toml") as data_file:
            lastTime.update(toml.load(data_file))


def writeLastTime():
    """Write the options to the config file."""
    fh = open("plomConfig.toml", "w")
    fh.write(toml.dumps(lastTime))
    fh.close()


# -------------------------------------------
# This is a very very cut-down version of annotator
# So we can automate some random marking of papers


class SceneParent(QWidget):
    def __init__(self):
        super(SceneParent, self).__init__()
        self.view = PageView(self)
        self.negComments = ["Careful", "Algebra", "Arithmetic", "Sign error", "Huh?"]
        self.posComments = ["Nice", "Well done", "Good", "Clever approach"]
        self.ink = QPen(Qt.red, 2)

    def doStuff(self, imageNames, saveName, maxMark, markStyle):
        self.saveName = saveName
        self.imageFiles = imageNames
        self.markStyle = markStyle
        self.maxMark = maxMark
        if markStyle == 2:
            self.score = 0
        else:
            self.score = maxMark

        self.scene = PageScene(
            self, imageNames, saveName, maxMark, self.score, markStyle
        )
        self.view.connectScene(self.scene)

    def getComments(self):
        return self.scene.getComments()

    def saveMarkerComments(self):
        commentList = self.getComments()
        # savefile is <blah>.png, save comments as <blah>.json
        with open(self.saveName[:-3] + "json", "w") as commentFile:
            json.dump(commentList, commentFile)

    def pickleIt(self):
        lst = self.scene.pickleSceneItems()  # newest items first
        lst.reverse()  # so newest items last
        plomDict = {
            "fileNames": [os.path.basename(fn) for fn in self.imageFiles],
            "saveName": os.path.basename(self.saveName),
            "markStyle": self.markStyle,
            "maxMark": self.maxMark,
            "currentMark": self.score,
            "sceneItems": lst,
        }
        # save pickled file as <blah>.plom
        plomFile = self.saveName[:-3] + "plom"
        with open(plomFile, "w") as fh:
            json.dump(plomDict, fh)

    def rpt(self):
        return QPointF(
            random.randint(100, 800) / 1000 * self.X,
            random.randint(100, 800) / 1000 * self.Y,
        )

    def TQX(self):
        c = random.choice([CommandTick, CommandCross, CommandQMark])
        self.scene.undoStack.push(c(self.scene, self.rpt()))

    def BE(self):
        c = random.choice([CommandBox, CommandEllipse])
        self.scene.undoStack.push(c(self.scene, QRectF(self.rpt(), self.rpt())))

    def LA(self):
        c = random.choice([CommandArrow, CommandLine, CommandArrowDouble])
        self.scene.undoStack.push(c(self.scene, self.rpt(), self.rpt()))

    def PTH(self):
        pth = QPainterPath()
        pth.moveTo(self.rpt())
        for k in range(random.randint(1, 4)):
            pth.lineTo(self.rpt())
        c = random.choice([CommandPen, CommandHighlight, CommandPenArrow])
        self.scene.undoStack.push(c(self.scene, pth))

    def GDT(self):
        blurb = TextItem(self, 12)
        dlt = random.choice([1, -1])
        if self.markStyle == 2:  # mark up
            dlt *= random.randint(0, self.maxMark - self.scene.score) // 2
            if dlt <= 0:  # just text
                blurb.setPlainText(random.choice(self.negComments))
                blurb.setPos(self.rpt())
                self.scene.undoStack.push(CommandText(self.scene, blurb, self.ink))
            else:
                blurb.setPlainText(random.choice(self.posComments))
                self.scene.undoStack.push(
                    CommandGDT(self.scene, self.rpt(), dlt, blurb, 12)
                )
        else:  # mark up
            dlt *= random.randint(0, self.scene.score) // 2
            if dlt >= 0:  # just text
                blurb.setPlainText(random.choice(self.posComments))
                blurb.setPos(self.rpt())
                self.scene.undoStack.push(CommandText(self.scene, blurb, self.ink))
            else:
                blurb.setPlainText(random.choice(self.negComments))
                self.scene.undoStack.push(
                    CommandGDT(self.scene, self.rpt(), dlt, blurb, 12)
                )

    def doRandomAnnotations(self):
        br = self.scene.underImage.boundingRect()
        self.X = br.width()
        self.Y = br.height()

        for k in range(8):
            random.choice([self.TQX, self.BE, self.LA, self.PTH])()
        for k in range(5):
            self.GDT()

    def doneAnnotating(self):
        plomFile = self.saveName[:-3] + "plom"
        commentFile = self.saveName[:-3] + "json"
        self.scene.save()
        # Save the marker's comments
        self.saveMarkerComments()
        # Pickle the scene as a plom-file
        self.pickleIt()
        return self.scene.score

    def changeMark(self, delta):
        self.score += delta


def annotatePaper(task, imageList, tags):
    print("Do stuff to task ", task)
    print("Tags are ", tags)
    # Image names = "<task>.<imagenumber>.png"
    with tempfile.TemporaryDirectory() as td:
        inames = []
        for i in range(len(imageList)):
            tmp = os.path.join(td, "{}.{}.png".format(task, i))
            inames.append(tmp)
            with open(tmp, "wb+") as fh:
                fh.write(imageList[i])
        annot = SceneParent()
        annot.doStuff(inames, "argh.png", 10, random.choice([2, 3]))
        annot.doRandomAnnotations()
        return annot.doneAnnotating()


def startMarking(question, version):
    print("Start work on question {} version {}".format(question, version))
    mx = messenger.MgetMaxMark(question, version)
    print("Maximum mark = ", mx)
    k = 0
    while True:
        task = messenger.MaskNextTask(question, version)
        if task is None:
            print("No more tasks.")
            break
        # print("Trying to claim next ask = ", task)
        try:
            print("Marking task ", task)
            imageList, tags = messenger.MclaimThisTask(task)
            score = annotatePaper(task, imageList, tags)
            messenger.MreturnMarkedTask(
                task,
                question,
                version,
                score,
                random.randint(1, 100),
                "",
                "argh.png",
                "argh.plom",
                "argh.json",
            )

        except PlomBenignException as e:
            print("Another user got that task. Trying again.")

    pass


# -------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run the marker-server test script. No arguments = run as normal."
    )

    parser.add_argument("-pwd", "--password", type=str)
    parser.add_argument(
        "-s", "--server", help="Which server to contact (must specify port as well)."
    )
    parser.add_argument(
        "-p", "--port", help="Which port to use (must specify server as well)."
    )
    args = parser.parse_args()

    # must spec both server+port or neither.
    if args.server and args.port:
        messenger.startMessenger(altServer=args.server, altPort=args.port)
    elif args.server is None and args.port is None:
        messenger.startMessenger()
    else:
        print("You must specify both the server and the port. Quitting.")
        quit()

    # get the password if not specified
    if args.password is None:
        try:
            pwd = getpass.getpass("Please enter the 'scanner' password:")
        except Exception as error:
            print("ERROR", error)
    else:
        pwd = args.password

    # get started
    try:
        messenger.requestAndSaveToken("scanner", pwd)
    except PlomExistingLoginException:
        print(
            "You appear to be already logged in!\n\n"
            "  * Perhaps a previous session crashed?\n"
            "  * Do you have another scanner-script running,\n"
            "    e.g., on another computer?\n\n"
            "In order to force-logout the existing authorisation run the 018_clearScannerLogin.py script."
        )
        messenger.clearAuthorisation("scanner", pwd)
        exit(0)

    spec = messenger.getInfoGeneral()
    print(spec)

    app = QApplication(sys.argv)
    for q in range(1, spec["numberOfQuestions"] + 1):
        for v in range(1, spec["numberOfVersions"] + 1):
            print("Annotating question {} version {}".format(q, v))
            startMarking(q, v)

    messenger.closeUser()
    messenger.stopMessenger()
