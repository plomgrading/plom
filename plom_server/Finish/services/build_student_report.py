# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Edith Coates
# Copyright (C) 2023-2024 Colin B. Macdonald
# Copyright (C) 2023-2024 Andrew Rechnitzer
# Copyright (C) 2024 Bryan Tanady

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import random
import tempfile
import time
from typing import Any

import arrow
import zipfly

from django.conf import settings
from django.core.files import File
from django.db import transaction
from django.db.models import Q
from django.core.exceptions import ObjectDoesNotExist
from django_huey import db_task, get_queue

from plom.finish.coverPageBuilder import makeCover

from Identify.models import PaperIDTask
from Mark.models import MarkingTask
from Mark.services import MarkingTaskService
from Papers.models import Paper, IDPage, DNMPage
from Papers.services import SpecificationService
from Progress.services import ManageScanService

from ..models import BuildStudentReportChore
from Base.models import HueyTaskTracker

from .student_marks_service import StudentMarkService

#REMOVE THIS: FOR TEST
from .ReportPDFService import pdf_builder


class BuildStudentReportService:
    """Class that contains helper functions for sending data to plom-finish (for building student report)."""

    build_report_dir = settings.MEDIA_ROOT / "build_report"

    def get_completion_status(self) -> dict[int, tuple[bool, bool, int, datetime]]:
        """Return a dictionary of overall test completion progress."""
        spreadsheet_data = {}
        papers = Paper.objects.all()
        for paper in papers:
            spreadsheet_data[paper.paper_number] = (
                StudentMarkService().get_paper_status(paper)
            )
        return spreadsheet_data

    def build_report(self, paper: Paper, *, outdir: Path | None = None) -> Path:
        """Build a student report for a single test paper.

        Args:
            paper: Paper instance to be built a student report.

        Keyword Args:
            outdir: pathlib.Path, the directory to save the test PDF
                or a default if omitted.

        Returns:
            pathlib.Path: the full path of the student report test PDF.
        """
        if outdir is None:
            outdir = Path("student_report")

        # Do we actually need this given the type-hints... I guess is safer.
        outdir = Path(outdir)
        outdir.mkdir(exist_ok=True)

        paper_id = StudentMarkService.get_paper_id_or_none(paper)
        if not paper_id:
            raise ValueError(
                f"Paper {paper.paper_number} is missing student ID information."
            )
        student_id, student_name = paper_id

        if not StudentMarkService().is_paper_marked(paper):
            raise ValueError(f"Paper {paper.paper_number} is not fully marked.")

        shortname = SpecificationService.get_shortname()
        outname = outdir / f"{shortname}_student_report_{student_id}.pdf"
        report = pdf_builder(versions=True)
        with open(outname, "wb") as pdf_file:
            pdf_file.write(report["bytes"])
        return outname
            
    def get_all_paper_status_for_report_building(self) -> list[dict[str, Any]]:
        """Get the status information for all papers for report building.

        Returns:
            List of dicts representing each row of the data.
        """
        status: dict[int, dict[str, Any]] = {}
        all_papers = Paper.objects.all()
        for paper in all_papers:
            status[paper.paper_number] = {
                "paper_num": int(paper.paper_number),
                "scanned": False,
                "identified": False,
                "marked": False,
                "number_marked": 0,
                "student_id": "",
                "last_update": None,
                "last_update_humanised": None,
                "build_report_status": "",
                "build_report_time": None,
                "build_report_time_humanised": None,
                "outdated": False,
                "obsolete": None,
            }
        mss = ManageScanService()
        number_of_questions = SpecificationService.get_n_questions()

        for pn in mss.get_all_completed_test_papers():
            status[pn]["scanned"] = True

        def latest_update(time_a: datetime | None, time_b: datetime) -> datetime:
            if time_a is None:
                return time_b
            elif time_a < time_b:
                return time_b
            else:
                return time_a

        for task in PaperIDTask.objects.filter(
            status=PaperIDTask.COMPLETE
        ).prefetch_related("paper", "latest_action"):
            status[task.paper.paper_number]["identified"] = True
            status[task.paper.paper_number][
                "student_id"
            ] = task.latest_action.student_id

            status[task.paper.paper_number]["last_update"] = latest_update(
                status[task.paper.paper_number]["last_update"], task.last_update
            )

        for task in MarkingTask.objects.filter(
            status=PaperIDTask.COMPLETE
        ).prefetch_related("paper"):
            status[task.paper.paper_number]["number_marked"] += 1
            status[task.paper.paper_number]["last_update"] = latest_update(
                status[task.paper.paper_number]["last_update"], task.last_update
            )

        # TODO: the status will be "" if no Chore or only obsolete Chores
        for task in BuildStudentReportChore.objects.filter(
            obsolete=False
        ).prefetch_related("paper"):
            status[task.paper.paper_number][
                "build_report_status"
            ] = task.get_status_display()
            # TODO: is always True
            status[task.paper.paper_number]["obsolete"] = task.obsolete
            if task.status == HueyTaskTracker.COMPLETE:
                status[task.paper.paper_number]["build_report_time"] = task.last_update
                status[task.paper.paper_number]["build_report_time_humanised"] = (
                    arrow.get(task.last_update).humanize()
                )

        # do last round of updates
        for pn in status:
            if status[pn]["number_marked"] == number_of_questions:
                status[pn]["marked"] = True
            if status[pn]["last_update"]:
                status[pn]["last_update_humanised"] = arrow.get(
                    status[pn]["last_update"]
                ).humanize()
            if status[pn]["build_report_time"] and status[pn]["last_update"]:
                if status[pn]["build_report_time"] < status[pn]["last_update"]:
                    status[pn]["outdated"] = True

        # we used the keys of paper number to build it but now keep only the rows
        return list(status.values())

    def queue_single_report(self, paper_num: int) -> None:
        """Create and queue a huey task to build student report for the given paper.

        If the report was already built, it will be first made obsolete.

        Args:
            paper_num: The paper number to be made a report.
        """
        try:
            paper = Paper.objects.get(paper_number=paper_num)
        except Paper.DoesNotExist:
            raise ValueError("No paper with that number") from None

        # mark any existing ones obsolete
        try:
            self.reset_single_report(paper_num)
        except ObjectDoesNotExist:
            pass

        with transaction.atomic(durable=True):
            if BuildStudentReportChore.objects.filter(
                paper=paper, obsolete=False
            ).exists():
                raise ValueError(
                    f"There are non-obsolete BuildStudentReportChores for papernum {paper_num}:"
                    " make them obsolete before creating another"
                )
            chore = BuildStudentReportChore.objects.create(
                paper=paper,
                huey_id=None,
                status=BuildStudentReportChore.STARTING,
            )
            chore.save()
            tracker_pk = chore.pk

        bsrs = huey_build_report(
            paper_num, tracker_pk=tracker_pk, _debug_be_flaky=False
        )
        print(f"Just enqueued Huey build student report task id={bsrs.id}")
        HueyTaskTracker.transition_to_queued_or_running(tracker_pk, bsrs.id)

    @transaction.atomic
    def get_single_student_report(self, paper_number: int) -> File:
        """Get the django-file of the student report pdf of the given paper.

        Args:
            paper_number (int): The paper number to re-assemble.

        Returns:
            File: the django-File of the student report pdf.

        Raises:
            ObjectDoesNotExist: no such paper or build student pdf chore, or if
                the report building is still in-progress.  TODO: maybe we'd
                like a different exception for the in-progress case.
        """
        chore = BuildStudentReportChore.objects.get(
            paper__paper_number=paper_number,
            obsolete=False,
            status=BuildStudentReportChore.COMPLETE,
        )
        return chore.pdf_file

    def try_to_cancel_single_queued_chore(self, paper_num: int) -> None:
        """Mark a report building chore as obsolete and try to cancel it if queued in Huey.

        Args:
            paper_num: The paper number of the chore to cancel.

        Raises:
            ObjectDoesNotExist: no such paper number or not chore for paper.

        This is a "best-attempt" at catching report building chores while they
        are queued.  It might be possible for a Chore to sneak past from the
        "Starting" state.  Already "Running" chores are not effected, although
        they ARE marked as obsolete.
        """
        chore = BuildStudentReportChore.objects.get(
            obsolete=False, paper__paper_number=paper_num
        )
        chore.set_as_obsolete()
        if chore.huey_id:
            queue = get_queue("tasks")
            queue.revoke_by_id(str(chore.huey_id))
        if chore.status in (BuildStudentReportChore.STARTING, BuildStudentReportChore.QUEUED):
            chore.transition_to_error("never ran: forcibly dequeued")

    def try_to_cancel_all_queued_chores(self) -> int:
        """Loop over all not-yet-running chores, marking them obsolete and cancelling (if possible) any in Huey.

        This is a "best-attempt" at catching report building chores while they
        are queued.  It might be possible for a Chore to sneak past from the
        "Starting" state.  Already "Running" chores should not be effected.

        Completed chores are uneffected.

        Returns:
            The number of chores that we tried to revoke (and/or stopped
            before the reached the queue).
        """
        N = 0
        queue = get_queue("tasks")
        with transaction.atomic(durable=True):
            for chore in BuildStudentReportChore.objects.filter(
                Q(status=BuildStudentReportChore.STARTING)
                | Q(status=BuildStudentReportChore.QUEUED)
            ).select_for_update():
                chore.set_as_obsolete()
                if chore.huey_id:
                    queue.revoke_by_id(str(chore.huey_id))
                chore.transition_to_error("never ran: forcibly dequeued")
                N += 1
        return N

    def reset_single_report(
        self, paper_num: int, *, wait: int | None = None
    ) -> None:
        """Obsolete the report building of a paper.

        Args:
            paper_num: The paper number of the student report building task to reset.

        Keyword Args:
            wait: how long to wait on running chores.  ``None`` is the
                default which means don't wait.  If you specify an integer,
                we will wait for that many seconds; raise a HueyException
                if the chore has not finished in time.  Note ``0`` is not
                quite the same as ``None`` because ``None`` will not cause
                an exception.

        Raises:
            ObjectDoesNotExist: no such paper number or not chore for paper.
            HueyException: timed out waiting for result.
        """
        chore = BuildStudentReportChore.objects.filter(
            obsolete=False, paper__paper_number=paper_num
        ).get()
        chore.set_as_obsolete()
        if chore.status == HueyTaskTracker.QUEUED:
            queue = get_queue("tasks")
            queue.revoke_by_id(str(chore.huey_id))
            chore.transition_to_error("never ran: forcibly dequeued")
        if chore.status == HueyTaskTracker.RUNNING:
            if wait is None:
                print(
                    f"Note: Chore running: {chore.huey_id};"
                    " we marked it obsolete but otherwise ignoring"
                )
            else:
                print(f"Chore running: {chore.huey_id}, we will wait for {wait}s...")
                r = queue.result(
                    str(chore.huey_id), blocking=True, timeout=wait, preserve=True
                )
                print(
                    f"The running task {chore.huey_id} has finished, and returned {r}"
                )

    def reset_all_reports(self) -> None:
        """Reset all building report chores, including completed ones."""
        # TODO: future work for a waiting version, see WIP below?
        wait = None
        # first cancel all queued chores
        self.try_to_cancel_all_queued_chores()
        # any ones that we did not obsolete, we'll get 'em now:
        for chore in BuildStudentReportChore.objects.filter(obsolete=False).all():
            chore.set_as_obsolete()
            if chore.status == HueyTaskTracker.RUNNING:
                if wait is None:
                    print(
                        f"Note: Chore running: {chore.huey_id};"
                        " we marked it obsolete but otherwise ignoring"
                    )
                else:
                    raise NotImplementedError(
                        f"waiting on the chore running: {chore.huey_id}"
                    )

    def _WIP_reset_all_report(self) -> None:
        """Reset all report building tasks and remove any associated pdfs.

        This tries to somewhat gracefully ("like an eagle...piloting a blimp")
        revoke queued tasks, wait for running tasks, etc.

        Raises:
            HueyException: timed out waiting for result, if we had to
                wait more than around (at least) 15 seconds total.
                The total time we could wait for success in unlikely
                worst case is ``10 + (5-epsilon)(# of running tasks)``.
        """
        total_wait = 15
        tries = 10
        blocking_wait = total_wait - tries * 1

        queue = get_queue("tasks")

        # I believe all this is racey and we cannot prevent something from slipping
        # between cases: we do multiple passes through to hopefully resolve that but
        # it still feels sloppy.  Perhaps this code should be looking on the queue,
        # talking to Huey rather than the Tracker's 2nd source of truth.

        while tries > 0:
            how_many_running = 0
            for task in BuildStudentReportChore.objects.filter(obsolete=False).all():
                if task.status == HueyTaskTracker.QUEUED:
                    queue.revoke_by_id(str(task.huey_id))
                elif task.status == HueyTaskTracker.RUNNING:
                    how_many_running += 1
                    print(f"There is a running task: {task.huey_id}")
                else:
                    task.set_as_obsolete()
            if how_many_running > 0:
                print(
                    f"There are {how_many_running} running task(s): "
                    f"waiting for {tries} more seconds..."
                )
                time.sleep(0.95)
            time.sleep(0.05)
            tries -= 1
            # in principle, we could leave the loop early whenever
            # how_many_running = 0 but I worry about race from STARTING
            # to QUEUED and others I haven't thought of.

        # Finally, blocking wait on any running, HueyException on timeout
        for task in BuildStudentReportChore.objects.filter(obsolete=False).all():
            task.set_as_obsolete()
            if task.status == HueyTaskTracker.RUNNING:
                print(
                    f"There is STILL a running task: {task.huey_id}, "
                    f"blocking wait for {blocking_wait}s before exception!"
                )
                r = queue.result(
                    str(task.huey_id),
                    blocking=True,
                    timeout=blocking_wait,
                    preserve=True,
                )
                print(f"The running task {task.huey_id} has finished, and returned {r}")

    def queue_all_report(self) -> None:
        """Queue the report building task of all papers that are ready (id'd and marked)."""
        # first work out which papers are ready
        for data in self.get_all_paper_status_for_report_building():
            # check if both id'd and marked
            if not data["identified"] or not data["marked"]:
                continue
            # check if already queued or complete
            # TODO: "Queued" is really `get_status_display` of HueyTaskTracker enum
            if data["build_report_status"] == "Queued":
                continue
            # TODO: "Complete" is really `get_status_display` of HueyTaskTracker enum
            if data["build_report_status"] == "Complete" and not data["outdated"]:
                # is complete and not outdated
                continue
            self.queue_single_report(data["paper_num"])

    @transaction.atomic
    def get_completed_pdf_files(self) -> list[File]:
        """Get list of paths of pdf-files of student reports that are not obsolete.

        Returns:
            A list of django-Files of the built report.
        """
        return [
            task.pdf_file
            for task in BuildStudentReportChore.objects.filter(
                obsolete=False, status=HueyTaskTracker.COMPLETE
            )
        ]

    @transaction.atomic
    def get_zipfly_generator(self, short_name: str, *, chunksize: int = 1024 * 1024):
        paths = [
            {
                "fs": pdf_file.path,
                "n": pdf_file.name,
            }
            for pdf_file in self.get_completed_pdf_files()
        ]

        zfly = zipfly.ZipFly(paths=paths, chunksize=chunksize)
        return zfly.generator()


# The decorated function returns a ``huey.api.Result``
# ``context=True`` so that the task knows its ID etc.
# TODO: investigate "preserve=True" here if we want to wait on them?
@db_task(queue="tasks", context=True)
def huey_build_report(
    paper_number: int, *, tracker_pk: int, task=None, _debug_be_flaky: bool = False
) -> bool:
    """Build student report for a single paper, updating the database with progress and resulting PDF.

    Args:
        paper_number: which paper to be built a student report.

    Keyword Args:
        tracker_pk: a key into the database for anyone interested in
            our progress.
        task: includes our ID in the Huey process queue.
        _debug_be_flaky: for debugging, all take a while and some
            percentage will fail.

    Returns:
        True, no meaning, just as per the Huey docs: "if you need to
        block or detect whether a task has finished".
    """
    try:
        paper_obj = Paper.objects.get(paper_number=paper_number)
    except Paper.DoesNotExist:
        raise ValueError("No paper with that number") from None

    HueyTaskTracker.transition_to_running(tracker_pk, task.id)

    bsrs = BuildStudentReportService()
    with tempfile.TemporaryDirectory() as tempdir:
        save_path = bsrs.build_report(paper_obj, outdir=Path(tempdir))

        if _debug_be_flaky:
            for i in range(5):
                print(f"Huey sleep i={i}/4: {task.id}")
                time.sleep(1)
            roll = random.randint(1, 10)
            if roll % 5 == 0:
                raise ValueError(
                    f"DEBUG: deliberately failing creation of student report for paper {paper_number}"
                )

        with transaction.atomic():
            chore = BuildStudentReportChore.objects.select_for_update().get(pk=tracker_pk)
            if not chore.obsolete:
                with save_path.open("rb") as f:
                    chore.pdf_file = File(f, name=save_path.name)
                    chore.save()

    HueyTaskTracker.transition_to_complete(tracker_pk)
    return True
