# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020-2021 Andrew Rechnitzer
# Copyright (C) 2020-2022 Colin B. Macdonald
# Copyright (C) 2020 Victoria Schuster

import json
from pathlib import Path
import random
import sys
import tempfile
import time

from PyQt5.QtCore import Qt, QPointF, QRectF
from PyQt5.QtGui import QPainterPath, QPen
from PyQt5.QtWidgets import QApplication, QWidget

from plom.plom_exceptions import PlomTakenException, PlomExistingLoginException
from plom.client.pageview import PageView
from plom.client.pagescene import PageScene

from plom.client.tools import (
    CommandTick,
    CommandCross,
    CommandQMark,
    CommandBox,
    CommandEllipse,
    CommandArrow,
    CommandLine,
    CommandArrowDouble,
    CommandPen,
    CommandHighlight,
    CommandPenArrow,
    CommandGroupDeltaText,
    CommandText,
)

from plom.messenger import Messenger
from .pagecache import download_pages


# comments which will be made into rubrics by pushing them to server and getting back keys
# need different ones for each question
negativeComments = [
    ("-1", "Careful"),
    ("-1", "Algebra"),
    ("-1", "Arithmetic"),
    ("-2", "Sign error"),
    ("-2", "Huh?"),
]
positiveComments = [
    ("+1", "Yes"),
    ("+1", "Nice"),
    ("+1", "Well done"),
    ("+2", "Good"),
    ("+2", "Clever approach"),
]
negativeRubrics = {}
positiveRubrics = {}

tag_list = ["creative", "suspicious", "needs_review", "hall_of_fame", "needs_iic"]


class RW:
    """A dummy class needed for compatibility with pagescene."""

    def changeMark(self, a, b):
        pass


class SceneParent(QWidget):
    def __init__(self, question, maxMark):
        super().__init__()
        self.view = PageView(self)
        self.ink = QPen(Qt.red, 2)
        self.question = question
        self.maxMark = maxMark
        self.rubric_widget = RW()  # a dummy class needed for compat with pagescene.
        self.saveName = None

    def doStuff(self, src_img_data, saveName, maxMark, markStyle):
        self.saveName = Path(saveName)
        self.src_img_data = src_img_data

        self.scene = PageScene(self, src_img_data, maxMark, None)
        self.view.connectScene(self.scene)

    def pickleIt(self):
        aname = self.scene.save(self.saveName)
        lst = self.scene.pickleSceneItems()  # newest items first
        lst.reverse()  # so newest items last
        plomDict = {
            "base_images": self.src_img_data,
            "saveName": str(aname),
            "markState": self.scene.getMarkingState(),
            "maxMark": self.maxMark,
            "currentMark": self.scene.getScore(),
            "sceneItems": lst,
        }
        plomfile = self.saveName.with_suffix(".plom")
        with open(plomfile, "w") as fh:
            json.dump(plomDict, fh, indent="  ")
            fh.write("\n")
        return aname, plomfile

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

    def doRubric(self):
        if random.choice([-1, 1]) == 1:
            rubric = random.choice(positiveRubrics[self.question])
        else:
            rubric = random.choice(negativeRubrics[self.question])

        self.scene.changeTheRubric(
            rubric["delta"], rubric["text"], rubric["id"], rubric["kind"]
        )

        # only do rubric if it is legal
        if self.scene.isLegalRubric("relative", rubric["delta"]):
            self.scene.undoStack.push(
                CommandGroupDeltaText(
                    self.scene,
                    self.rpt(),
                    rubric["id"],
                    rubric["kind"],
                    rubric["delta"],
                    rubric["text"],
                )
            )
        else:  # not legal - push text
            self.scene.undoStack.push(
                CommandText(self.scene, self.rpt(), rubric["text"])
            )

    def doRandomAnnotations(self):
        br = self.scene.underImage.boundingRect()
        self.X = br.width()
        self.Y = br.height()

        for k in range(8):
            random.choice([self.TQX, self.BE, self.LA, self.PTH])()
        for k in range(5):
            # self.GDT()
            self.doRubric()
        self.scene.undoStack.push(
            CommandText(
                self.scene, QPointF(200, 100), "Random annotations for testing only."
            )
        )

    def doneAnnotating(self):
        aname, plomfile = self.pickleIt()
        return self.scene.score, self.scene.get_rubrics_from_page(), aname, plomfile

    def refreshDisplayedMark(self, score):
        # needed for compat with pagescene.py
        pass

    def setModeLabels(self, mode):
        # needed for compat with pagescene.py
        pass


def annotatePaper(question, maxMark, task, src_img_data, aname, tags):
    print("Starting random marking to task {}".format(task))
    annot = SceneParent(question, maxMark)
    annot.doStuff(src_img_data, aname, maxMark, random.choice([2, 3]))
    annot.doRandomAnnotations()
    # Issue #1391: settle annotation events, avoid races with QTimers
    Qapp.processEvents()
    time.sleep(0.25)
    Qapp.processEvents()
    return annot.doneAnnotating()


def do_random_marking_backend(question, version, *, messenger):
    maxMark = messenger.MgetMaxMark(question, version)

    while True:
        task = messenger.MaskNextTask(question, version)
        if task is None:
            print("No more tasks.")
            break
        # print("Trying to claim next ask = ", task)
        try:
            image_metadata, tags, integrity_check = messenger.MclaimThisTask(
                task, version=version
            )
        except PlomTakenException:
            print("Another user got task {}. Trying again...".format(task))
            continue

        src_img_data = [{"id": r[0], "md5": r[1]} for r in image_metadata]
        papernum = int(task[1:5])
        pagedata = messenger.get_pagedata_context_question(papernum, question)
        with tempfile.TemporaryDirectory() as td:
            pagedata = download_pages(messenger, pagedata, td, alt_get=src_img_data)
            # Populate the orientation keys from the full pagedata
            for row in src_img_data:
                ori = [r["orientation"] for r in pagedata if r["id"] == row["id"]]
                # There could easily be more than one: what if orientation is contradictory?
                row["orientation"] = ori[0]  # just take first one

            for row in src_img_data:
                for r in pagedata:
                    if r["md5"] == row["md5"]:
                        row["filename"] = r["local_filename"]

            basefile = Path(td) / "argh"
            score, rubrics, aname, plomfile = annotatePaper(
                question, maxMark, task, src_img_data, basefile, tags
            )
            print("Score of {} out of {}".format(score, maxMark))
            messenger.MreturnMarkedTask(
                task,
                question,
                version,
                score,
                random.randint(1, 20),
                aname,
                plomfile,
                rubrics,
                integrity_check,
                src_img_data,
            )
        # tag one in three papers
        if random.randrange(3) == 0:
            # use up to 3 tags, skewed towards single tag
            num_tag = random.choice([1] * 4 + [2] * 2 + [3])
            the_tags = []
            for k in range(num_tag):
                the_tag = random.choice(tag_list)
                if the_tag not in the_tags:
                    the_tags.append(the_tag)
                    messenger.add_single_tag(task, the_tag)
            print(f"Tagged task with: {the_tags}")


def build_random_rubrics(question, *, messenger):
    """Push random rubrics into a server: only for testing/demo purposes

    .. caution:: Do not use on a real production server.

    args:
        question (int)

    keyword args:
        messenger: a messenger object already connected to the server.

    returns:
        None
    """
    for (d, t) in positiveComments:
        com = {
            "delta": d,
            "text": t,
            "tags": "Random",
            "meta": "Randomness",
            "kind": "relative",
            "question": question,
        }
        com["id"] = messenger.McreateRubric(com)[1]
        if question in positiveRubrics:
            positiveRubrics[question].append(com)
        else:
            positiveRubrics[question] = [com]
    for (d, t) in negativeComments:
        com = {
            "delta": d,
            "text": t,
            "tags": "Random",
            "meta": "Randomness",
            "kind": "relative",
            "question": question,
        }
        com["id"] = messenger.McreateRubric(com)[1]
        if question in negativeRubrics:
            negativeRubrics[question].append(com)
        else:
            negativeRubrics[question] = [com]


def do_rando_marking(server, user, password):
    """Randomly annotate the papers assigning RANDOM grades: only for testing please.

    .. caution:: Only for testing/demos.  Do not use for real tests.

    Also, for each paper, with probability 1/3, we tag with up to 3
    randomly selected tags.

    args:
        server (str)
        user (str)
        password (str)

    returns:
        int: 0 on success, non-zero on error/unexpected.
    """
    global Qapp

    if server and ":" in server:
        s, p = server.split(":")
        messenger = Messenger(s, port=p)
    else:
        messenger = Messenger(server)
    messenger.start()

    try:
        messenger.requestAndSaveToken(user, password)
    except PlomExistingLoginException:
        print(
            "You appear to be already logged in!\n\n"
            "  * Perhaps a previous session crashed?\n"
            "  * Do you have another scanner-script running,\n"
            "    e.g., on another computer?\n\n"
            "This script has automatically force-logout'd that user."
        )
        messenger.clearAuthorisation(user, password)
        return 1

    try:
        spec = messenger.get_spec()

        # Headless QT: https://stackoverflow.com/a/35355906
        L = sys.argv
        L.extend(["-platform", "offscreen"])
        Qapp = QApplication(L)

        for q in range(1, spec["numberOfQuestions"] + 1):
            build_random_rubrics(q, messenger=messenger)
            for v in range(1, spec["numberOfVersions"] + 1):
                print("Annotating question {} version {}".format(q, v))
                do_random_marking_backend(q, v, messenger=messenger)
    finally:
        messenger.closeUser()
        messenger.stop()
    return 0
