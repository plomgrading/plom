# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2022 Brennen Chiu
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2023 Julian Lapenna
# Copyright (C) 2023 Colin B. Macdonald

import pathlib
import random
from tempfile import TemporaryDirectory

import zipfly

from plom.create.mergeAndCodePages import make_PDF

from django.conf import settings
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.db import transaction
from django.core.files import File
from django_huey import db_task
from django_huey import get_queue

from Papers.models import Paper
from Preparation.models import PaperSourcePDF
from Base.models import HueyTaskTracker
from ..models import PDFHueyTask


# The decorated function returns a ``huey.api.Result``
# ``context=True`` so that the task knows its ID etc.
@db_task(queue="tasks", context=True)
def huey_build_single_paper(
    papernum: int,
    spec: dict,
    question_versions: dict,
    *,
    tracker_pk: int,
    task=None,
    quiet: bool = True,
    _debug_be_flaky: bool = False,
) -> None:
    """Build a single paper.

    It is important to understand that running this function starts an
    async task in queue that will run sometime in the future.

    Args:
        papernum:
        spec:
        question_versions:

    Keyword Args:
        tracker_pk: a key into the database for anyone interested in
            our progress.
        task: includes our ID in the Huey process queue.
        quiet: a hack so the Huey process started signal is ignored
            TODO: perhaps to be removed later.  The signal handler
            itself gets a list of our args and looks for this.
        _debug_be_flaky: for debugging, fail some percentage of their
            building.

    Returns:
        None
    """
    with transaction.atomic():
        tr = HueyTaskTracker.objects.get(pk=tracker_pk)
        tr.status = HueyTaskTracker.RUNNING
        tr.huey_id = task.id
        tr.save()

    with TemporaryDirectory() as tempdir:
        save_path = make_PDF(
            spec=spec,
            papernum=papernum,
            question_versions=question_versions,
            where=pathlib.Path(tempdir),
            source_versions_path=PaperSourcePDF.upload_to(),
        )

        if _debug_be_flaky:
            roll = random.randint(1, 10)
            if roll % 5 == 0:
                raise ValueError(
                    f"DEBUG: deliberately failing creation of papernum={papernum}"
                )

        paper = Paper.objects.get(paper_number=papernum)
        tr = paper.pdfhueytask
        # TODO: which way is "better"?
        tr2 = PDFHueyTask(pk=tracker_pk)
        assert tr == tr2
        with save_path.open("rb") as f:
            tr.pdf_file = File(f, name=save_path.name)
            tr.status = HueyTaskTracker.COMPLETE
            tr.save()


# The decorated function returns a ``huey.api.Result``
# ``context=True`` so that the task knows its ID etc.
@db_task(queue="tasks", context=True)
def huey_build_prenamed_paper(
    papernum: int,
    spec: dict,
    question_versions: dict,
    student_info: dict,
    *,
    tracker_pk: int,
    task=None,
    quiet: bool = True,
    _debug_be_flaky: bool = False,
) -> None:
    """Build a single paper and prename it.

    It is important to understand that running this function starts an
    async task in queue that will run sometime in the future.

    Args:
        papernum:
        spec:
        question_versions:
        student_info:

    Keyword Args:
        tracker_pk: a key into the database for anyone interested in
            our progress.
        task: includes our ID in the Huey process queue.
        quiet: a hack so the Huey process started signal is ignored
            TODO: perhaps to be removed later.  The signal handler
            itself gets a list of our args and looks for this.
        _debug_be_flaky: for debugging, fail some percentage of their
            building.

    Returns:
        None
    """
    with transaction.atomic():
        tr = HueyTaskTracker.objects.get(pk=tracker_pk)
        tr.status = HueyTaskTracker.RUNNING
        tr.huey_id = task.id
        tr.save()

    with TemporaryDirectory() as tempdir:
        save_path = make_PDF(
            spec=spec,
            papernum=papernum,
            question_versions=question_versions,
            extra=student_info,
            where=pathlib.Path(tempdir),
            source_versions_path=PaperSourcePDF.upload_to(),
        )

        if _debug_be_flaky:
            roll = random.randint(1, 10)
            if roll % 5 == 0:
                raise ValueError(
                    f"DEBUG: deliberately failing creation of papernum={papernum}"
                )

        paper = Paper.objects.get(paper_number=papernum)
        tr = paper.pdfhueytask
        # TODO: which way is "better"?
        tr2 = PDFHueyTask(pk=tracker_pk)
        assert tr == tr2
        with save_path.open("rb") as f:
            tr.pdf_file = File(f, name=save_path.name)
            tr.status = HueyTaskTracker.COMPLETE
            tr.save()


class BuildPapersService:
    """Generate and stamp test-paper PDFs."""

    base_dir = settings.MEDIA_ROOT
    papers_to_print = base_dir / "papersToPrint"

    @transaction.atomic
    def get_n_complete_tasks(self):
        """Get the number of PDFHueyTasks that have completed."""
        return PDFHueyTask.objects.filter(status=PDFHueyTask.COMPLETE).count()

    @transaction.atomic
    def get_n_pending_tasks(self):
        """Get the number of PDFHueyTasks with the status other than 'COMPLETE'."""
        return PDFHueyTask.objects.exclude(status=PDFHueyTask.COMPLETE).count()

    @transaction.atomic
    def get_n_running_tasks(self):
        """Get the number of PDFHueyTasks with the status 'STARTING', 'QUEUED' or 'RUNNING'."""
        return PDFHueyTask.objects.filter(
            Q(status=PDFHueyTask.STARTING)
            | Q(status=PDFHueyTask.QUEUED)
            | Q(status=PDFHueyTask.RUNNING)
        ).count()

    @transaction.atomic
    def get_n_tasks(self):
        """Get the total number of PDFHueyTasks."""
        return PDFHueyTask.objects.all().count()

    @transaction.atomic
    def are_all_papers_built(self):
        """Return True if all of the test-papers have been successfully built."""
        total_tasks = self.get_n_tasks()
        complete_tasks = self.get_n_complete_tasks()
        return total_tasks > 0 and total_tasks == complete_tasks

    @transaction.atomic
    def are_there_errors(self):
        """Return True if there are any PDFHueyTasks with an 'error' status."""
        return PDFHueyTask.objects.filter(status=PDFHueyTask.ERROR).count() > 0

    def _create_task_to_do(
        self, papernum: int, *, student_name=None, student_id=None
    ) -> None:
        """Create and save a PDF-building task to the database, but don't start it."""
        paper = get_object_or_404(Paper, paper_number=papernum)

        task = PDFHueyTask(
            paper=paper,
            huey_id=None,
            status=PDFHueyTask.TO_DO,
            student_name=student_name,
            student_id=student_id,
        )
        task.save()

    def get_completed_pdf_paths(self):
        """Get list of paths of pdf-files of completed (built) tests papers."""
        return [
            pdf.file_path()
            for pdf in PDFHueyTask.objects.filter(status=PDFHueyTask.COMPLETE)
        ]

    def stage_all_pdf_jobs(self, classdict=None):
        """Create all the PDFHueyTasks, and save to the database without sending them to Huey.

        If there are prenamed test-papers, save that info too.
        """
        # note - classdict is a list of dicts - change this to more useful format
        prenamed = {X["paper_number"]: X for X in classdict if X["paper_number"] > 0}

        self.papers_to_print.mkdir(exist_ok=True)
        for paper_obj in Paper.objects.all():
            paper_number = paper_obj.paper_number
            student_name = None
            student_id = None
            if paper_number in prenamed:
                student_id = prenamed[paper_number]["id"]
                student_name = prenamed[paper_number]["studentName"]

            self._create_task_to_do(
                paper_number,
                student_id=student_id,
                student_name=student_name,
            )

    def send_all_tasks(self, spec, qvmap):
        """Send all marked as todo PDF tasks to huey."""
        todo_tasks = PDFHueyTask.objects.filter(status=PDFHueyTask.TO_DO)
        for task in todo_tasks:
            paper_number = task.paper.paper_number
            self._send_single_task(task, paper_number, spec, qvmap[paper_number])

    def send_single_task(self, paper_num, spec, qv_row):
        """Send a single todo task to Huey.

        TODO: nothing here asserts it is really status TO_DO, nor that
        the tracker already exists.  Perhaps this is only used for retries
        or similar?
        """
        paper = get_object_or_404(Paper, paper_number=paper_num)
        task = paper.pdfhueytask
        self._send_single_task(task, paper_num, spec, qv_row)

    def _send_single_task(self, task, paper_num, spec, qv_row):
        with transaction.atomic(durable=True):
            task.status = HueyTaskTracker.STARTING
            task.save()
            tracker_pk = task.pk

        if task.student_name and task.student_id:
            info_dict = {"id": task.student_id, "name": task.student_name}
            _ = huey_build_prenamed_paper(
                paper_num, spec, qv_row, info_dict, tracker_pk=tracker_pk, quiet=True
            )
        else:
            _ = huey_build_single_paper(
                paper_num, spec, qv_row, tracker_pk=tracker_pk, quiet=True
            )

        with transaction.atomic(durable=True):
            task = HueyTaskTracker.objects.get(pk=tracker_pk)
            # if its still starting, it is safe to change to queued
            if task.status == HueyTaskTracker.STARTING:
                task.status = HueyTaskTracker.QUEUED
                task.save()

    def cancel_all_task(self):
        """Cancel all queued task from Huey."""
        queue_tasks = PDFHueyTask.objects.filter(status=PDFHueyTask.QUEUED)
        for task in queue_tasks:
            queue = get_queue("tasks")
            queue.revoke_by_id(task.huey_id)
            task.status = PDFHueyTask.TO_DO
            task.save()

    def cancel_single_task(self, paper_number):
        """Cancel a single queued task from Huey.

        TODO!  document this, when can it be expected to work etc?
        """
        task = get_object_or_404(Paper, paper_number=paper_number).pdfhueytask
        queue = get_queue("tasks")
        queue.revoke_by_id(task.huey_id)
        task.status = PDFHueyTask.TO_DO
        task.save()

    def retry_all_task(self, spec, qvmap):
        """Retry all tasks that have error status."""
        retry_tasks = PDFHueyTask.objects.filter(status=PDFHueyTask.ERROR)
        for task in retry_tasks:
            paper_number = task.paper.paper_number
            self._send_single_task(task, paper_number, spec, qvmap[paper_number])

    @transaction.atomic
    def reset_all_tasks(self):
        self.cancel_all_task()
        for task in PDFHueyTask.objects.all():
            task.file_path().unlink(missing_ok=True)
            task.huey_id = None
            task.status = PDFHueyTask.TO_DO
            task.save()

    @transaction.atomic
    def get_all_task_status(self):
        """Get the status of every task and return as a dict."""
        stat = {}
        for task in PDFHueyTask.objects.all():
            stat[task.paper.paper_number] = task.get_status_display()
        return stat

    @transaction.atomic
    def get_paper_path_and_bytes(self, paper_number):
        """Get the bytes of the file generated by the given task."""
        try:
            task = Paper.objects.get(paper_number=paper_number).pdfhueytask
        except (Paper.DoesNotExist, PDFHueyTask.DoesNotExist):
            raise ValueError(f"Cannot find task {paper_number}")
        if task.status != PDFHueyTask.COMPLETE:
            raise ValueError(f"Task {paper_number} is not complete")

        paper_path = task.file_path()
        with paper_path.open("rb") as fh:
            return (paper_path.name, fh.read())

    @transaction.atomic
    def get_task_context(self):
        """Get information about all tasks."""
        return [
            {
                "paper_number": task.paper.paper_number,
                "status": task.get_status_display(),
                "message": task.message,
                "pdf_filename": task.file_display_name(),
            }
            for task in PDFHueyTask.objects.all()
            .select_related("paper")
            .order_by("paper__paper_number")
        ]

    def get_zipfly_generator(self, short_name, *, chunksize=1024 * 1024):
        bps = BuildPapersService()
        paths = [
            {
                "fs": pdf_path,
                "n": pathlib.Path(f"papers_for_{short_name}") / pdf_path.name,
            }
            for pdf_path in bps.get_completed_pdf_paths()
        ]

        zfly = zipfly.ZipFly(paths=paths, chunksize=chunksize)
        return zfly.generator()
