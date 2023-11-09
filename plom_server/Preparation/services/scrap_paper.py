# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2023 Colin B. Macdonald

import logging
from pathlib import Path
from tempfile import TemporaryDirectory

from django.core.files import File
from django.db import transaction
from django_huey import db_task

from ..models import ScrapPaperPDFHueyTask as ScrapPaperPDFTask


log = logging.getLogger("ScrapPaperService")


# The decorated function returns a ``huey.api.Result``
# ``context=True`` so that the task knows its ID etc.
@db_task(queue="tasks", context=True)
def huey_build_the_scrap_paper_pdf(task=None) -> None:
    """Build a single scrap paper pdf."""
    from plom.create import build_scrap_paper_pdf

    # build the pdf in a tempdirectory
    # there is redundancy here because that is what build_scrap_page_pdf does already...
    # TODO - simplify build_scrap_page_pdf to avoid this redundancy.

    with TemporaryDirectory() as tmpdirname:
        build_scrap_paper_pdf(destination_dir=tmpdirname)
        # the resulting file "scrap_paper.pdf" is build in
        # tmpdirname record that task is completed in database and
        # let it move file into place. Check that the task's
        # huey-id matches (as strings) the id supplied by the huey
        # worker. It should be!
        task_obj = ScrapPaperPDFTask.load()
        if str(task_obj.huey_id) != str(task.id):
            # Race condition: Issue #3134.
            # TODO: alternatively we could wait here for a bit and try again.
            # TODO: IMHO stop storing PDFs in the Tracker Issue #3136.
            raise ValueError(
                f"Task's huey id {task_obj.huey_id} does not match the id supplied by the huey worker {task.id}."
            )
        scp_path = Path(tmpdirname) / "scrap_paper.pdf"

        with scp_path.open(mode="rb") as fh:
            task_obj.scrap_paper_pdf = File(fh, name=scp_path.name)
            task_obj.save()


class ScrapPaperService:
    @transaction.atomic()
    def get_scrap_paper_task_status(self) -> str:
        """Status of the build scrap paper task, creating a "todo" task if it does not exist.

        Return:
            The status as string: "To Do", "Queued", "Started", "Error" or "Complete".

        """
        return ScrapPaperPDFTask.load().get_status_display()

    @transaction.atomic()
    def get_scrap_paper_pdf_filepath(self):
        return ScrapPaperPDFTask.load().scrap_paper_pdf.path

    @transaction.atomic()
    def delete_scrap_paper_pdf(self):
        # explicitly delete the file, and set status back to "todo" and huey-id back to none
        task_obj = ScrapPaperPDFTask.load()
        Path(task_obj.scrap_paper_pdf.path).unlink(missing_ok=True)
        task_obj.status = ScrapPaperPDFTask.TO_DO
        task_obj.huey_id = None
        task_obj.save()

    @transaction.atomic()
    def build_scrap_paper_pdf(self):
        """Enqueue the huey task of building the scrap paper pdf."""
        task_obj = ScrapPaperPDFTask.load()
        if task_obj.status == ScrapPaperPDFTask.COMPLETE:
            return
        res = huey_build_the_scrap_paper_pdf()
        # TODO: there is a race here b/c the _build function looks for this object by this id
        task_obj.huey_id = res.id
        task_obj.status = ScrapPaperPDFTask.QUEUED
        task_obj.save()

    @transaction.atomic
    def get_scrap_paper_pdf_as_bytes(self):
        scp_obj = ScrapPaperPDFTask.load()
        if scp_obj.status == ScrapPaperPDFTask.COMPLETE:
            with scp_obj.scrap_paper_pdf.open("rb") as fh:
                return fh.read()
        else:
            raise ValueError("Scrap paper pdf does not yet exist")
