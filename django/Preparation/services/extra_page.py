from django.conf import settings
from django.core.files import File
from django.db import transaction

from django_huey import db_task

from Preparation.models import ExtraPagePDFTask

import logging
from pathlib import Path

log = logging.getLogger("ExtraPageService")


class ExtraPageService:
    base_dir = settings.BASE_DIR
    papers_to_print = base_dir / "papersToPrint"

    @transaction.atomic()
    def get_extra_page_task_status(self):
        """Return the status of the build extra page task. If no such
        task then create one with status 'todo'

        """
        try:
            return ExtraPagePDFTask.objects.get().status
        except ExtraPagePDFTask.DoesNotExist:
            epp_obj = ExtraPagePDFTask(status="todo")
            epp_obj.save()
            return "todo"

    @transaction.atomic()
    def get_extra_page_pdf_filepath(self):
        try:
            return ExtraPagePDFTask.objects.get().extra_page_pdf.path
        except ExtraPagePDFTask.DoesNotExist:
            return None

    @transaction.atomic()
    def delete_extra_page_pdf(self):
        # explicitly delete the file, and set status back to "todo"
        # TODO - make this a bit cleaner.
        if ExtraPagePDFTask.objects.exists():
            Path(ExtraPagePDFTask.objects.get().extra_page_pdf.path).unlink(
                missing_ok=True
            )
            ExtraPagePDFTask.objects.filter().delete()
            # then create a new task with status = todo
            ExtraPagePDFTask.objects.create(status="todo")

    @db_task(queue="tasks", context=True)  # so that the task knows its ID etc.
    def _build_the_extra_page_pdf(task=None):
        """Build a single test-paper"""
        from plom.create import build_extra_page_pdf

        # TODO clean up the file handling here.
        # the resulting file "extra_page.pdf" is build in cwd
        build_extra_page_pdf()

        # record that task is completed in database and let it move file
        # into place. We can look up which record via the task.id == huey_id
        epp_obj = ExtraPagePDFTask.objects.get(huey_id=task.id)
        epp_path = Path("extra_page.pdf")
        with epp_path.open(mode="rb") as fh:
            epp_obj.extra_page_pdf = File(fh, name=epp_path.name)
            epp_obj.save()
        # The above is a *copy* not a move, so delete the original file
        epp_path.unlink()
        # TODO - work out better file wrangling so we don't have to delete this leftover.

    @transaction.atomic()
    def build_extra_page_pdf(self):
        """Enqueue the huey task of building the extra page pdf"""
        task_obj = ExtraPagePDFTask.objects.get()
        if task_obj.status == "complete":
            return
        pdf_build = self._build_the_extra_page_pdf()
        task_obj.huey_id = pdf_build.id
        task_obj.status = "queued"
        task_obj.save()

    @transaction.atomic
    def get_extra_page_pdf_as_bytes(self):
        epp_obj = ExtraPagePDFTask.objects.get()
        if epp_obj.status == "complete":
            with epp_obj.extra_page_pdf.open("rb") as fh:
                return fh.read()
        else:
            raise ValueError("Extra page pdf does not yet exist")
