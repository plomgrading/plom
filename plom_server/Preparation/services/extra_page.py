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
from ..models import ExtraPagePDFHueyTask as ExtraPagePDFTask


log = logging.getLogger("ExtraPageService")


# The decorated function returns a ``huey.api.Result``
# ``context=True`` so that the task knows its ID etc.
@db_task(queue="tasks", context=True)
def huey_build_the_extra_page_pdf(
    *, tracker_pk: int, task=None, quiet: bool = True
) -> None:
    """Build a single test-paper.

    Keyword Args:
        tracker_pk: a key into the database for anyone interested in
            our progress.
        task: includes our ID in the Huey process queue.
        quiet: a hack so the Huey process started signal is ignored
            TODO: perhaps to be removed later.  The signal handler
            itself gets a list of our args and looks for this.
    """
    from plom.create import build_extra_page_pdf

    with transaction.atomic():
        task_obj = ExtraPagePDFTask.load()
        task_obj.huey_id = task.id
        task_obj.status = HueyTaskTracker.RUNNING
        task_obj.save()

    # build the pdf in a tempdirectory
    # there is redundancy here because that is what build_extra_page_pdf does already...
    # TODO - simplify build_extra_page_pdf to avoid this redundancy.

    with TemporaryDirectory() as tmpdirname:
        build_extra_page_pdf(destination_dir=tmpdirname)
        # the resulting file "extra_page.pdf" is build in
        # tmpdirname record that task is completed in database and
        # let it move file into place.
        epp_path = Path(tmpdirname) / "extra_page.pdf"
        with epp_path.open(mode="rb") as fh:
            with transaction.atomic():
                # TODO: unclear to me if we need to re-get the task
                task_obj = ExtraPagePDFTask.load()
                task_obj.extra_page_pdf = File(fh, name=epp_path.name)
                task_obj.status = HueyTaskTracker.COMPLETE
                task_obj.save()


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

    def build_extra_page_pdf(self):
        """Enqueue the huey task of building the extra page pdf."""
        task_obj = ExtraPagePDFTask.load()
        if task_obj.status == HueyTaskTracker.COMPLETE:
            return
        with transaction.atomic(durable=True):
            task_obj.status = HueyTaskTracker.TO_DO
            task_obj.save()
            tracker_pk = task_obj.pk

        _ = huey_build_the_extra_page_pdf(tracker_pk=tracker_pk, quiet=True)
        # print(f"Just enqueued Huey extra page builder id={_.id}")

        with transaction.atomic(durable=True):
            task = HueyTaskTracker.objects.get(pk=tracker_pk)
            # if its still starting, it is safe to change to queued
            if task.status == HueyTaskTracker.STARTING:
                task.status = HueyTaskTracker.QUEUED
                task.save()

    @transaction.atomic
    def get_extra_page_pdf_as_bytes(self):
        epp_obj = ExtraPagePDFTask.load()
        if epp_obj.status == ExtraPagePDFTask.COMPLETE:
            with epp_obj.extra_page_pdf.open("rb") as fh:
                return fh.read()
        else:
            raise ValueError("Extra page pdf does not yet exist")
