from django.test import TestCase
from model_bakery import baker
from warnings import catch_warnings, simplefilter

from BuildPaperPDF.services import BuildPapersService
from BuildPaperPDF.models import PDFTask


class BuildPaperPDFTests(TestCase):
    """Test BuildPaperPDF.services.BuildPapersService"""

    def make_tasks(self):
        with catch_warnings():  # Don't worry about timezone naivete
            simplefilter("ignore")
            baker.make(PDFTask, status="todo")
            baker.make(PDFTask, status="started")
            baker.make(PDFTask, status="queued")
            baker.make(PDFTask, status="complete")
            baker.make(PDFTask, status="error")
            baker.make(PDFTask, status="complete")

    def test_get_n_complete_tasks(self):
        """test BuildPapersService.get_n_complete_tasks"""
        bps = BuildPapersService()
        n_complete = bps.get_n_complete_tasks()
        self.assertEqual(n_complete, 0)

        self.make_tasks()

        n_complete = bps.get_n_complete_tasks()
        self.assertEqual(n_complete, 2)

    def test_get_n_pending_tasks(self):
        """test BuildPapersService.get_n_pending_tasks"""
        bps = BuildPapersService()
        n_pending = bps.get_n_pending_tasks()
        self.assertEqual(n_pending, 0)

        self.make_tasks()

        n_pending = bps.get_n_pending_tasks()
        self.assertEqual(n_pending, 4)

    def test_get_n_tasks(self):
        """Test BuildPapersService.get_n_tasks"""
        bps = BuildPapersService()
        n_total = bps.get_n_tasks()
        self.assertEqual(n_total, 0)

        self.make_tasks()

        n_total = bps.get_n_tasks()
        self.assertEqual(n_total, 6)

    def test_get_n_running_tasks(self):
        """Test BuildPapersService.get_n_running_tasks"""
        bps = BuildPapersService()
        n_running = bps.get_n_running_tasks()
        self.assertEqual(n_running, 0)

        self.make_tasks()

        n_running = bps.get_n_running_tasks()
        self.assertEqual(n_running, 2)
