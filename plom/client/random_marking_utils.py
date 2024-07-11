# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020-2021 Andrew Rechnitzer
# Copyright (C) 2020-2024 Colin B. Macdonald
# Copyright (C) 2020 Victoria Schuster
# Copyright (C) 2023 Julian Lapenna
# Copyright (C) 2024 Aden Chan

import json
from pathlib import Path
import random
import sys
import tempfile
import time
from typing import Union, Iterable

# Yuck, replace this below when we drop Python 3.8 support
from typing import Dict, List

from PyQt6.QtCore import QPointF, QRectF
from PyQt6.QtGui import QColor, QPainterPath, QPen
from PyQt6.QtWidgets import QApplication, QWidget

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
    CommandRubric,
    CommandText,
)

from plom.messenger import Messenger
from .downloader import Downloader


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
negativeRubrics: Dict[int, List] = {}
positiveRubrics: Dict[int, List] = {}

tag_list = ["creative", "suspicious", "needs_review", "hall_of_fame", "needs_iic"]


class MockRubricWidget:
    """A dummy class needed for compatibility with pagescene."""

    def updateLegalityOfRubrics(self):
        pass


class SceneParent(QWidget):
    """This class is a cut-down Annotator for mock-testing the PageScene."""

    def __init__(self, question, maxMark, Qapp):
        super().__init__()
        self.view = PageView(self)
        self.ink = QPen(QColor("red"), 2)
        self.question = question
        self.maxMark = maxMark
        self.rubric_widget = MockRubricWidget()
        self.saveName = None
        self._Qapp = Qapp

    def is_experimental(self):
        return False

    def pause_to_process_events(self):
        """Allow Qt's event loop to process events.

        Typically we call this if we're in a loop of our own waiting
        for something to happen which can only occur if we
        """
        self._Qapp.processEvents()

    def rearrangePages(self):
        pass

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

    def do_rubric_any(self) -> None:
        """Place some rubric or maybe just some text, randomly."""
        if random.choice([-1, 1]) == 1:
            rubric = random.choice(positiveRubrics[self.question])
        else:
            rubric = random.choice(negativeRubrics[self.question])

        self.scene.setCurrentRubric(rubric)
        self.scene.setToolMode("rubric")

        # only do rubric if it is legal
        if self.scene.isLegalRubric(rubric):
            self.scene.undoStack.push(CommandRubric(self.scene, self.rpt(), rubric))
        else:  # not legal - push text
            self.scene.undoStack.push(
                CommandText(self.scene, self.rpt(), rubric["text"])
            )

    def do_rubric_change_score(self) -> None:
        """Keep trying to place score-changing rubric until we succeed."""
        while True:
            if random.choice([-1, 1]) == 1:
                rubric = random.choice(positiveRubrics[self.question])
            else:
                rubric = random.choice(negativeRubrics[self.question])

            self.scene.setCurrentRubric(rubric)
            self.scene.setToolMode("rubric")

            if self.scene.isLegalRubric(rubric):
                if rubric["value"] > 0 or rubric["value"] < 0:
                    self.scene.undoStack.push(
                        CommandRubric(self.scene, self.rpt(), rubric)
                    )
                    return

    def doRandomAnnotations(self):
        br = self.scene.underImage.boundingRect()
        self.X = br.width()
        self.Y = br.height()

        for k in range(8):
            random.choice([self.TQX, self.BE, self.LA, self.PTH])()
        #  we must do *something* to set the score, Issue #3323
        self.do_rubric_change_score()
        for k in range(4):
            self.do_rubric_any()
        self.scene.undoStack.push(
            CommandText(
                self.scene, QPointF(200, 100), "Random annotations for testing only."
            )
        )

    def doneAnnotating(self) -> tuple:
        aname, plomfile = self.pickleIt()
        return self.scene.score, self.scene.get_rubric_ids(), aname, plomfile

    def refreshDisplayedMark(self, score) -> None:
        # needed for compat with pagescene.py
        pass


def annotatePaper(
    question, maxMark, task, src_img_data, aname, tags, *, Qapp: QApplication
) -> tuple:
    print("Starting random marking to task {}".format(task))
    annot = SceneParent(question, maxMark, Qapp)
    annot.doStuff(src_img_data, aname, maxMark, random.choice([2, 3]))
    annot.doRandomAnnotations()
    # Issue #1391: settle annotation events, avoid races with QTimers
    annot.pause_to_process_events()
    time.sleep(0.25)
    annot.pause_to_process_events()
    return annot.doneAnnotating()


def do_random_marking_backend(
    question: int, version: int, *, Qapp: QApplication, messenger, partial: float
) -> None:
    maxMark = messenger.getMaxMark(question)
    remarking_counter = 0

    while True:
        task = messenger.MaskNextTask(question, version)
        if task is None:
            print("No more tasks.")
            break
        # print("Trying to claim next ask = ", task)
        try:
            src_img_data, tags, integrity_check = messenger.MclaimThisTask(
                task, version=version
            )
        except PlomTakenException:
            print("Another user got task {}. Trying again...".format(task))
            continue

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

        # skip marking some percentage of paper-questions
        if random.random() * 100 > partial:
            print("Skipping task {}".format(task))
            continue

        with tempfile.TemporaryDirectory() as td:
            downloader = Downloader(td, msgr=messenger)
            src_img_data = downloader.sync_downloads(src_img_data)

            basefile = Path(td) / "argh"
            score, rubrics, aname, plomfile = annotatePaper(
                question, maxMark, task, src_img_data, basefile, tags, Qapp=Qapp
            )
            print("Score of {} out of {}".format(score, maxMark))
            messenger.MreturnMarkedTask(
                task,
                question,
                version,
                score,
                max(0, round(random.gauss(180, 50))),
                aname,
                plomfile,
                rubrics,
                integrity_check,
            )

            # remark every 6th paper
            if (remarking_counter % 6) == 0:
                score, rubrics, aname, plomfile = annotatePaper(
                    question, maxMark, task, src_img_data, basefile, tags, Qapp=Qapp
                )
                print("Remarking to {} out of {}".format(score, maxMark))
                messenger.MreturnMarkedTask(
                    task,
                    question,
                    version,
                    score,
                    max(0, round(random.gauss(180, 50))),
                    aname,
                    plomfile,
                    rubrics,
                    integrity_check,
                )
        remarking_counter += 1


def build_random_rubrics(question_idx: int, *, username, messenger) -> None:
    """Push random rubrics into a server: only for testing/demo purposes.

    .. caution:: Do not use on a real production server.

    Args:
        question_idx: which question.

    Keyword Args:
        messenger: a messenger object already connected to the server.
        username (str): which username to create the rubrics.

    Returns:
        None
    """
    for d, t in positiveComments:
        com = {
            "value": int(d),
            "display_delta": d,
            "out_of": 0,
            "text": t,
            "tags": "Random",
            "meta": "Randomness",
            "kind": "relative",
            "question": question_idx,
            "username": username,
        }
        com = messenger.McreateRubric(com)
        if question_idx in positiveRubrics:
            positiveRubrics[question_idx].append(com)
        else:
            positiveRubrics[question_idx] = [com]
    for d, t in negativeComments:
        com = {
            "value": int(d),
            "display_delta": d,
            "out_of": 0,
            "text": t,
            "tags": "Random",
            "meta": "Randomness",
            "kind": "relative",
            "question": question_idx,
            "username": username,
        }
        com = messenger.McreateRubric(com)
        if question_idx in negativeRubrics:
            negativeRubrics[question_idx].append(com)
        else:
            negativeRubrics[question_idx] = [com]


def do_rando_marking(
    server: Union[str, None],
    user: str,
    password: str,
    *,
    partial: float = 100.0,
    question: Union[None, int] = None,
    version: Union[None, int] = None,
) -> int:
    """Randomly annotate the papers assigning RANDOM grades: only for testing please.

    .. caution:: Only for testing/demos.  Do not use for real tests.

    Also, for each paper, with probability 1/3, we tag with up to 3
    randomly selected tags.

    Args:
        server: which server.
        user: credientials.
        password: credientials.

    Keyword Args:
        partial: what percentage of papers to grade?
        question: what question to mark or if omitted, mark all of them.
        version: what version to mark or if omitted, mark all of them.

    Returns:
        0 on success, non-zero on error/unexpected.
    """
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

        if question is None:
            questions: Iterable = range(1, spec["numberOfQuestions"] + 1)
        else:
            questions = [question]

        if version is None:
            versions: Iterable = range(1, spec["numberOfVersions"] + 1)
        else:
            versions = [version]

        for q in questions:
            build_random_rubrics(q, username=user, messenger=messenger)
            for v in versions:
                print(f"Annotating question {q} version {v}")
                do_random_marking_backend(
                    q, v, Qapp=Qapp, messenger=messenger, partial=partial
                )
    finally:
        messenger.closeUser()
        messenger.stop()
    return 0
