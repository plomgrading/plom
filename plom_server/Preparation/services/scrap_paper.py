# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2023 Colin B. Macdonald

import logging
from pathlib import Path
from tempfile import TemporaryDirectory

from django.core.files import File
from django.db import transaction
from django_huey import db_task

from Base.models import HueyTaskTracker
from ..models import ScrapPaperPDFHueyTask as ScrapPaperPDFTask


log = logging.getLogger("ScrapPaperService")


# The decorated function returns a ``huey.api.Result``
# ``context=True`` so that the task knows its ID etc.
@db_task(queue="tasks", context=True)
def huey_build_the_scrap_paper_pdf(*, tracker_pk: int, task=None) -> None:
    """Build a single scrap paper pdf.

    Keyword Args:
        tracker_pk: a key into the database for anyone interested in
            our progress.
        task: includes our ID in the Huey process queue.
    """
    from plom.create import build_scrap_paper_pdf

    with transaction.atomic():
        task_obj = ScrapPaperPDFTask.load().transition_to_running(task.id)

    # build the pdf in a tempdirectory
    # there is redundancy here because that is what build_scrap_page_pdf does already...
    # TODO - simplify build_scrap_page_pdf to avoid this redundancy.

    with TemporaryDirectory() as tmpdirname:
        build_scrap_paper_pdf(destination_dir=tmpdirname)
        # the resulting file "scrap_paper.pdf" is build in
        # tmpdirname record that task is completed in database and
        # let it move file into place.
        scp_path = Path(tmpdirname) / "scrap_paper.pdf"
        with scp_path.open(mode="rb") as fh:
            with transaction.atomic():
                # TODO: unclear to me if we need to re-get the task
                task_obj = ScrapPaperPDFTask.load()
                task_obj.scrap_paper_pdf = File(fh, name=scp_path.name)
                task_obj.transition_to_complete()


class ScrapPaperService:
    @transaction.atomic()
    def get_scrap_paper_task_status(self) -> str:
        """Status of the build scrap paper task, creating a "to do" task if it does not exist.

        Return:
            The status as string: "To do", "Starting", "Queued", "Running",
            "Error" or "Complete", as defined in the HueyTaskTracker class.
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
        task_obj.transition_back_to_todo()

    def build_scrap_paper_pdf(self):
        """Enqueue the huey task of building the scrap paper pdf."""
        task_obj = ScrapPaperPDFTask.load()
        if task_obj.status == HueyTaskTracker.COMPLETE:
            return
        with transaction.atomic(durable=True):
            task_obj.transition_to_starting()
            tracker_pk = task_obj.pk

        res = huey_build_the_scrap_paper_pdf(tracker_pk=tracker_pk)
        # print(f"Just enqueued Huey scrap paper builder id={res.id}")

        with transaction.atomic(durable=True):
            tr = HueyTaskTracker.objects.get(pk=tracker_pk)
            tr.transition_to_queued_or_running(res.id)

    @transaction.atomic
    def get_scrap_paper_pdf_as_bytes(self):
        scp_obj = ScrapPaperPDFTask.load()
        if scp_obj.status == ScrapPaperPDFTask.COMPLETE:
            with scp_obj.scrap_paper_pdf.open("rb") as fh:
                return fh.read()
        else:
            raise ValueError("Scrap paper pdf does not yet exist")
