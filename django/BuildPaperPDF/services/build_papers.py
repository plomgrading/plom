from plom.create.buildDatabaseAndPapers import build_papers
from huey.signals import SIGNAL_EXECUTING, SIGNAL_COMPLETE, SIGNAL_ERROR

from django.conf import settings
from django_huey import get_queue, db_task

from BuildPaperPDF.models import Task


class BuildPapersService:
    """Use Core Plom to build test-papers."""

    def create_task(self, index: int, huey_id: id):
        """Create and save a PDF-building task to the database"""
        paper_path = settings.BASE_DIR / 'papersToPrint' / f"exam_{index:04}.pdf"
        task = Task(
            paper_number=index,
            huey_id=huey_id,
            pdf_file_path=str(paper_path),
            status='todo',
        )
        task.save()
        return task

    def build_n_papers(self, n, credentials):
        """Build multiple papers without having to sign in/out each time"""
        for i in range(n):
            self.build_single_paper(i + 1, credentials)

    def build_single_paper(self, index: int, credentials):
        """Build a single test-paper (with huey!)"""
        pdf_build = self._build_single_paper(index, credentials)
        task_obj = self.create_task(index, pdf_build.id)
        task_obj.status = 'queued'
        task_obj.save()
        return task_obj

    @db_task(queue="tasks")
    def _build_single_paper(index: int, credentials):
        """Build a single test-paper"""
        build_papers(
            basedir=settings.BASE_DIR,
            indexToMake=index,
            msgr=credentials
        )

    def build_all_papers(self, ccs):
        """Build all the test-papers."""
        msgr = None
        try:
            msgr = ccs.get_manager_messenger()
            msgr.start()
            msgr.requestAndSaveToken(ccs.manager_username, ccs.get_manager_password())

            build_papers(
                basedir=settings.BASE_DIR,
                msgr=msgr
            )
        finally:
            if msgr:
                if msgr.token:
                    msgr.clearAuthorisation(ccs.manager_username, ccs.get_manager_password())
                msgr.stop()
