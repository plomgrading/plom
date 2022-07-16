# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2019-2021 Andrew Rechnitzer
# Copyright (C) 2019-2022 Colin B. Macdonald
# Copyright (C) 2020 Victoria Schuster

"""
Tools for downloading images / pagedata in background threads.
"""

import logging

from PyQt5.QtCore import (
    QThread,
    pyqtSignal,
)

from plom.plom_exceptions import (
    PlomSeriousException,
    PlomTakenException,
)
from .pagecache import download_pages


log = logging.getLogger("bgdownload")


class BackgroundDownloader(QThread):
    """
    Downloads exams in background.

    Notes:
        Read https://mayaposch.wordpress.com/2011/11/01/how-to-really-truly-use-qthreads-the-full-explanation/
        and https://stackoverflow.com/questions/6783194/background-thread-with-qthread-in-pyqt
        and finally https://woboq.com/blog/qthread-you-were-not-doing-so-wrong.html
        (Done in the simpler subclassing way.)

    """

    downloadSuccess = pyqtSignal(str, list, list, list, str)
    downloadNoneAvailable = pyqtSignal()
    downloadFail = pyqtSignal(str)

    def __init__(self, question, version, msgr_clone, *, workdir, tag=None, above=None):
        """
        Initializes a new downloader.

        Args:
            question (str): question number
            version (str): version number.
            msgr_clone (Messenger): use this for the actual downloads.
                Note Messenger is not multithreaded and blocks using
                mutexes, so you may want to pass a clone of your
                Messenger, rather than the one you are using yourself!

        Keyword Args:
            workdir (pathlib.Path): filespace for downloading.
            tag (str/None): if we prefer tagged papers.
            above (int/None): if we prefer papers above a certain
                paper number.

        Notes:
            question/version may be able to be type int as well.
        """
        super().__init__()
        self.question = question
        self.version = version
        self.workingDirectory = workdir
        self._msgr = msgr_clone
        self.tag = tag
        self.above = above

    def run(self):
        """
        Runs the background downloader.

        Notes:
            Overrides run method of QThread.

        Returns:
            None

        """
        attempts = 0
        while True:
            attempts += 1
            # little sanity check - shouldn't be needed.
            # TODO remove.
            if attempts > 5:
                return
            # ask server for task-code of next task
            try:
                log.debug("bgdownloader: about to download")
                # TODO: does not yet read tagging preference
                task = self._msgr.MaskNextTask(
                    self.question, self.version, tag=self.tag, above=self.above
                )
                if not task:  # no more tests left
                    self.downloadNoneAvailable.emit()
                    self.quit()
                    return
            except PlomSeriousException as err:
                self.downloadFail.emit(str(err))
                self.quit()
                return

            try:
                page_metadata, tags, integrity_check = self._msgr.MclaimThisTask(
                    task, version=self.version
                )
                break
            except PlomTakenException as err:
                log.info("will keep trying as task already taken: {}".format(err))
                continue
            except PlomSeriousException as err:
                self.downloadFail.emit(str(err))
                self.quit()

        src_img_data = [{"id": x[0], "md5": x[1]} for x in page_metadata]
        del page_metadata

        num = int(task[1:5])
        pagedata = self._msgr.get_pagedata_context_question(num, self.question)
        pagedata = download_pages(
            self._msgr, pagedata, self.workingDirectory, alt_get=src_img_data
        )
        # don't save in _full_pagedata b/c we're in another thread: see downloadSuccess emitted below

        # Populate the orientation keys from the full pagedata
        for row in src_img_data:
            ori = [r["orientation"] for r in pagedata if r["id"] == row["id"]]
            # There could easily be more than one: what if orientation is contradictory?
            row["orientation"] = ori[0]  # just take first one

        for row in src_img_data:
            for r in pagedata:
                if r["md5"] == row["md5"]:
                    row["filename"] = r["local_filename"]

        self.downloadSuccess.emit(task, src_img_data, pagedata, tags, integrity_check)
        self.quit()
