from django.test import TestCase
from model_bakery import baker

from BuildPaperPDF.services import BuildPapersService
from BuildPaperPDF.models import PDFTask


class BuildPaperPDFTests(TestCase):
    """Test BuildPaperPDF.services.BuildPapersService"""

    def test_get_n_complete_tasks(self):
        """test BuildPapersService.get_n_complete_tasks"""
        bps = BuildPapersService()
        n_complete = bps.get_n_complete_tasks()
        self.assertEqual(n_complete, 0)

        baker.make(PDFTask, status='todo')
        baker.make(PDFTask, status='queued')
        baker.make(PDFTask, status='complete')
        baker.make(PDFTask, status='error')
        baker.make(PDFTask, status="complete")
        n_complete = bps.get_n_complete_tasks()
        self.assertEqual(n_complete, 2)

    def test_get_n_pending_tasks(self):
        """test BuildPapersService.get_n_pending_tasks"""
        bps = BuildPapersService()
        n_pending = bps.get_n_pending_tasks()
        self.assertEqual(n_pending, 0)

        baker.make(PDFTask, status='todo')
        baker.make(PDFTask, status='queued')
        baker.make(PDFTask, status='complete')
        baker.make(PDFTask, status='error')
        baker.make(PDFTask, status="complete")
        n_pending = bps.get_n_pending_tasks()
        self.assertEqual(n_pending, 3)
