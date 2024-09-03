# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2022 Brennen Chiu
# Copyright (C) 2023-2024 Colin Macdonald

from django.test import TestCase
from model_bakery import baker
from warnings import catch_warnings, simplefilter

from .services import BuildPapersService
from .models import BuildPaperPDFChore


class BuildPaperPDFTests(TestCase):
    """Test BuildPaperPDF.services.BuildPapersService."""

    def make_tasks(self):
        with catch_warnings():  # Don't worry about timezone naivete
            simplefilter("ignore")
            baker.make(BuildPaperPDFChore, status=BuildPaperPDFChore.STARTING)
            baker.make(BuildPaperPDFChore, status=BuildPaperPDFChore.QUEUED)
            baker.make(BuildPaperPDFChore, status=BuildPaperPDFChore.RUNNING)
            baker.make(BuildPaperPDFChore, status=BuildPaperPDFChore.COMPLETE)
            baker.make(BuildPaperPDFChore, status=BuildPaperPDFChore.ERROR)
            baker.make(BuildPaperPDFChore, status=BuildPaperPDFChore.COMPLETE)

    def test_get_n_complete_tasks(self) -> None:
        """Test BuildPapersService.get_n_complete_tasks."""
        bps = BuildPapersService()
        n_complete = bps.get_n_complete_tasks()
        self.assertEqual(n_complete, 0)

        self.make_tasks()

        n_complete = bps.get_n_complete_tasks()
        self.assertEqual(n_complete, 2)

    def test_get_n_tasks(self) -> None:
        """Test BuildPapersService.get_n_tasks."""
        bps = BuildPapersService()
        n_total = bps.get_n_tasks()
        self.assertEqual(n_total, 0)

        self.make_tasks()

        n_total = bps.get_n_tasks()
        self.assertEqual(n_total, 6)

    def test_get_n_tasks_started_but_not_complete(self) -> None:
        """Test BuildPapersService checking how many in progress."""
        bps = BuildPapersService()
        n_running = bps.get_n_tasks_started_but_not_complete()
        self.assertEqual(n_running, 0)

        self.make_tasks()

        n_running = bps.get_n_tasks_started_but_not_complete()
        self.assertEqual(n_running, 3)
