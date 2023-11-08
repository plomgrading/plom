# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2023 Colin B. Macdonald

import logging
from pathlib import Path
from tempfile import TemporaryDirectory

from django.core.files import File
from django.db import transaction
from django_huey import db_task

from ..models import ExtraPagePDFHueyTask as ExtraPagePDFTask


log = logging.getLogger("ExtraPageService")


class ExtraPageService:
    @transaction.atomic()
    def get_extra_page_task_status(self) -> str:
        """Status of the build extra page task, creating a "todo" task if it does not exist.

        Return:
            The status as string: "To do", "Queued", "Started", "Error" or "Complete".

        """
        return ExtraPagePDFTask.load().get_status_display()

    @transaction.atomic()
    def get_extra_page_pdf_filepath(self):
        return ExtraPagePDFTask.load().extra_page_pdf.path

    @transaction.atomic()
    def delete_extra_page_pdf(self):
        # explicitly delete the file, and set status back to "todo" and huey-id back to none
        task_obj = ExtraPagePDFTask.load()
        Path(task_obj.extra_page_pdf.path).unlink(missing_ok=True)
        task_obj.status = ExtraPagePDFTask.TO_DO
        task_obj.huey_id = None
        task_obj.save()

    @db_task(queue="tasks", context=True)  # so that the task knows its ID etc.
    def _build_the_extra_page_pdf(task=None):
        """Build a single test-paper."""
        from plom.create import build_extra_page_pdf

        # build the pdf in a tempdirectory
        # there is redundancy here because that is what build_extra_page_pdf does already...
        # TODO - simplify build_extra_page_pdf to avoid this redundancy.

        with TemporaryDirectory() as tmpdirname:
            build_extra_page_pdf(destination_dir=tmpdirname)
            # the resulting file "extra_page.pdf" is build in
            # tmpdirname record that task is completed in database and
            # let it move file into place. Check that the task's
            # huey-id matches (as strings) the id supplied by the huey
            # worker. It should be!
            task_obj = ExtraPagePDFTask.load()
            if str(task_obj.huey_id) != str(task.id):
                raise ValueError(
                    f"Task's huey id {task_obj.huey_id} does not match the id supplied by the huey worker {task.id}."
                )
            epp_path = Path(tmpdirname) / "extra_page.pdf"
            with epp_path.open(mode="rb") as fh:
                task_obj.extra_page_pdf = File(fh, name=epp_path.name)
                task_obj.save()

    @transaction.atomic()
    def build_extra_page_pdf(self):
        """Enqueue the huey task of building the extra page pdf."""
        task_obj = ExtraPagePDFTask.load()
        if task_obj.status == ExtraPagePDFTask.COMPLETE:
            return
        pdf_build = self._build_the_extra_page_pdf()
        task_obj.huey_id = pdf_build.id
        task_obj.status = ExtraPagePDFTask.QUEUED
        task_obj.save()

    @transaction.atomic
    def get_extra_page_pdf_as_bytes(self):
        epp_obj = ExtraPagePDFTask.load()
        if epp_obj.status == ExtraPagePDFTask.COMPLETE:
            with epp_obj.extra_page_pdf.open("rb") as fh:
                return fh.read()
        else:
            raise ValueError("Extra page pdf does not yet exist")
