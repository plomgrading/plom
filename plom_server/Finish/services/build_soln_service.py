# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023-2025 Colin B. Macdonald
# Copyright (C) 2023-2025 Andrew Rechnitzer

import io
import random
import tempfile
import time
from pathlib import Path
from typing import Any

import arrow
import pymupdf
import zipfly

from django.core.exceptions import ObjectDoesNotExist
from django.core.files import File
from django.db import transaction
from django.db.models import Q
from django_huey import db_task, get_queue
import huey
import huey.api

from plom_server.Scan.services import ManageScanService
from plom_server.Base.models import HueyTaskTracker
from plom_server.Identify.models import PaperIDTask
from plom_server.Papers.models import (
    SolnSpecQuestion,
    Paper,
    QuestionPage,
)
from plom_server.Papers.services import SpecificationService
from ..models import SolutionSourcePDF, BuildSolutionPDFChore
from .student_marks_service import StudentMarkService
from .soln_source import SolnSourceService
from .reassemble_service import ReassembleService


class BuildSolutionService:
    """Class that contains helper functions for sending data to plom-finish."""

    def get_all_paper_status_for_solution_build(self) -> list[dict[str, Any]]:
        """Get the status information for all papers for solution build.

        Returns:
            List of dicts representing each row of the data.
        """
        status: dict[str, Any] = {}
        all_papers = Paper.objects.all()
        for paper in all_papers:
            status[paper.paper_number] = {
                "paper_num": int(paper.paper_number),
                "scanned": False,
                "identified": False,
                "student_id": "",
                "when_id_done": None,
                "when_id_done_humanised": None,
                "build_soln_status": "",
                "build_soln_time": None,
                "build_soln_time_humanised": None,
                "outdated": False,
                "obsolete": None,
            }
        for pn in ManageScanService.get_all_complete_papers():
            status[pn]["scanned"] = True

        for task in PaperIDTask.objects.filter(
            status=PaperIDTask.COMPLETE
        ).prefetch_related("paper", "latest_action"):
            status[task.paper.paper_number]["identified"] = True
            status[task.paper.paper_number][
                "student_id"
            ] = task.latest_action.student_id
            status[task.paper.paper_number]["when_id_done"] = task.last_update

        for task in BuildSolutionPDFChore.objects.filter(
            obsolete=False
        ).prefetch_related("paper"):
            status[task.paper.paper_number][
                "build_soln_status"
            ] = task.get_status_display()
            status[task.paper.paper_number]["obsolete"] = task.obsolete
            if task.status == HueyTaskTracker.COMPLETE:
                status[task.paper.paper_number]["build_soln_time"] = task.last_update
                status[task.paper.paper_number]["build_soln_time_humanised"] = (
                    arrow.get(task.last_update).humanize()
                )

        # do last round of updates
        for pn in status:
            if status[pn]["when_id_done"]:
                status[pn]["when_id_done_humanised"] = arrow.get(
                    status[pn]["when_id_done"]
                ).humanize()
            # if soln pdf built before last id-ing of the paper, then soln pdf is outdated.
            if status[pn]["build_soln_time"] and status[pn]["when_id_done"]:
                if status[pn]["build_soln_time"] < status[pn]["when_id_done"]:
                    status[pn]["outdated"] = True

        # we used the keys of paper number to build it but now keep only the rows
        return list(status.values())

    def watermark_pages(self, doc: pymupdf.Document, watermark_text: str) -> None:
        """Watermark the pages of the given document with the given text."""
        margin = 10
        for pg in doc:
            h = pg.rect.height
            wm_rect = pymupdf.Rect(margin, h - margin - 32, margin + 200, h - margin)
            excess = pg.insert_textbox(
                wm_rect,
                watermark_text,
                fontsize=18,
                color=(0, 0, 0),
                align=1,
                stroke_opacity=0.33,
                fill_opacity=0.33,
                overlay=True,
            )
            assert (
                excess > 0
            ), f"Text didn't fit: is SID label too long? {watermark_text}"
            pg.draw_rect(wm_rect, color=[0, 0, 0], stroke_opacity=0.25)

    def assemble_solution_for_paper(
        self, paper_number: int, *, watermark: bool = False
    ) -> tuple[bytes, str]:
        """Reassemble the solutions for a particular question into a PDF file, returning bytes.

        Args:
            paper_number: which paper to build solutions for.

        Keyword Args:
            watermark: whether to paint watermarked student ids.
                Defaults to False.

        Returns:
            A tuple of the bytes for a PDF file and a suggested filename.
        """
        try:
            paper_obj = Paper.objects.get(paper_number=paper_number)
        except ObjectDoesNotExist:
            raise ValueError(f"Cannot find paper {paper_number}")

        if not SolnSourceService().are_all_solution_pdf_present():
            raise ValueError(
                "Cannot assemble solutions until all source solution pdfs uploaded"
            )
        # get the version of each question
        qv_map = {}
        for qp_obj in QuestionPage.objects.filter(paper=paper_obj):
            qv_map[qp_obj.question_index] = qp_obj.version
        # get the solution pdfs
        soln_doc = {}
        for spdf_obj in SolutionSourcePDF.objects.all():
            soln_doc[spdf_obj.version] = pymupdf.open(spdf_obj.source_pdf.path)

        # build the solution coverpage in a tempdir
        # open it as a pymupdf doc and then append the soln pages to it.
        reas = ReassembleService()
        with tempfile.TemporaryDirectory() as tmpdir:
            cp_path = reas.build_paper_cover_page(
                Path(tmpdir), paper_obj, solution=True
            )
            with pymupdf.open(cp_path) as dest_doc:
                # now append required soln pages.
                # do this in order of the solution-number
                # see issue #3689
                for qi, v in sorted(qv_map.items()):
                    pg_list = SolnSpecQuestion.objects.get(question_index=qi).pages
                    # pg_list can be "[3]" or "[3, 4, 5]".
                    # minus one b/c pg_list is 1-indexed but pymupdf pages 0-indexed
                    dest_doc.insert_pdf(
                        soln_doc[v], from_page=pg_list[0] - 1, to_page=pg_list[-1] - 1
                    )

                shortname = SpecificationService.get_shortname()
                sid_sname_pair = StudentMarkService.get_paper_id_or_none(paper_obj)
                if sid_sname_pair:
                    # make sure filename matches legacy - see #3405
                    fname = f"{shortname}_solutions_{sid_sname_pair[0]}.pdf"
                    if watermark:
                        self.watermark_pages(
                            dest_doc, f"Solutions for {sid_sname_pair[0]}"
                        )
                else:
                    # make sure filename matches legacy - see #3405
                    fname = f"{shortname}_solutions_{paper_number:04}.pdf"

                return (dest_doc.tobytes(), fname)

    def reset_single_solution_build(
        self, paper_num: int, *, wait: int | None = None
    ) -> None:
        """Obsolete the solution build of a paper.

        Args:
            paper_num: The paper number of the solution build task to reset.

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
        chore = BuildSolutionPDFChore.objects.filter(
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
                    f"The running chore {chore.huey_id} has finished, and returned {r}"
                )

    def reset_all_soln_build(self) -> None:
        """Reset all build soln, including completed ones."""
        # TODO: future work for a waiting version, see WIP below?
        wait = None
        # first cancel all queued chores
        self.try_to_cancel_all_queued_chores()
        # any ones that we did not obsolete, we'll get 'em now:
        for chore in BuildSolutionPDFChore.objects.filter(obsolete=False).all():
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

    def queue_single_solution_build(self, paper_num: int) -> None:
        """Create and queue a huey task to build solution for the given paper.

        If the solution-PDF was already built, it will be first made obsolete.

        Args:
            paper_num: The paper number to build solutions for.
        """
        try:
            paper = Paper.objects.get(paper_number=paper_num)
        except Paper.DoesNotExist:
            raise ValueError("No paper with that number") from None

        # mark any existing ones obsolete
        try:
            self.reset_single_solution_build(paper_num)
        except ObjectDoesNotExist:
            pass

        with transaction.atomic(durable=True):
            if BuildSolutionPDFChore.objects.filter(
                paper=paper, obsolete=False
            ).exists():
                raise ValueError(
                    f"There are non-obsolete BuildSolutionPDFChores for papernum {paper_num}:"
                    " make them obsolete before creating another"
                )
            chore = BuildSolutionPDFChore.objects.create(
                paper=paper,
                huey_id=None,
                status=BuildSolutionPDFChore.STARTING,
            )
            chore.save()
            tracker_pk = chore.pk

        res = huey_build_soln_for_paper(
            paper_num, tracker_pk=tracker_pk, _debug_be_flaky=False
        )
        print(f"Just enqueued Huey solution build task id={res.id}")
        HueyTaskTracker.transition_to_queued_or_running(tracker_pk, res.id)

    def queue_all_solution_builds(self) -> None:
        """Queue the solution build for all all papers that have been used."""
        # first work out which papers have been used (ie have any pages)
        for data in self.get_all_paper_status_for_solution_build():
            # must be scanned to be ready for solution build
            if not data["scanned"]:
                continue
            # check if already queued or complete
            # TODO: "Queued" is really `get_status_display` of HueyTaskTracker enum
            if data["build_soln_status"] == "Queued":
                continue
            # TODO: "Complete" is really `get_status_display` of HueyTaskTracker enum
            if data["build_soln_status"] == "Complete" and not data["outdated"]:
                # is complete and not outdated
                continue
            self.queue_single_solution_build(data["paper_num"])

    @transaction.atomic
    def get_single_solution_pdf_file(self, paper_number: int) -> File:
        """Get the django-file of the solution pdf for the given paper.

        Args:
            paper_number (int): The paper number to re-assemble.

        Returns:
            File: the django-File of the solution pdf.

        Raises:
            ObjectDoesNotExist: no such paper or solution build chore, or if
                the solution build is still in-progress.  TODO: maybe we'd
                like a different exception for the in-progress case.
        """
        chore = BuildSolutionPDFChore.objects.get(
            paper__paper_number=paper_number,
            obsolete=False,
            status=BuildSolutionPDFChore.COMPLETE,
        )
        return chore.pdf_file

    def try_to_cancel_single_queued_chore(self, paper_num: int) -> None:
        """Mark a solution pdf build chore as obsolete and try to cancel it if queued in Huey.

        Args:
            paper_num: The paper number of the chore to cancel.

        Raises:
            ObjectDoesNotExist: no such paper number or not chore for paper.

        This is a "best-attempt" at catching soln-build chores while they
        are queued.  It might be possible for a Chore to sneak past from the
        "Starting" state.  Already "Running" chores are not effected, although
        they ARE marked as obsolete.
        """
        chore = BuildSolutionPDFChore.objects.get(
            obsolete=False, paper__paper_number=paper_num
        )
        chore.set_as_obsolete()
        if chore.huey_id:
            queue = get_queue("tasks")
            queue.revoke_by_id(str(chore.huey_id))
        if chore.status in (
            BuildSolutionPDFChore.STARTING,
            BuildSolutionPDFChore.QUEUED,
        ):
            chore.transition_to_error("never ran: forcibly dequeued")

    def try_to_cancel_all_queued_chores(self) -> int:
        """Loop over all not-yet-running chores, marking them obsolete and cancelling (if possible) any in Huey.

        This is a "best-attempt" at catching soln-build chores while they
        are queued.  It might be possible for a Chore to sneak past from the
        "Starting" state.  Already "Running" chores should not be effected.

        Completed chores are uneffected.

        Returns:
            The number of chores that we tried to revoke (and/or stopped
            before they reached the queue).
        """
        N = 0
        queue = get_queue("tasks")
        with transaction.atomic(durable=True):
            for chore in BuildSolutionPDFChore.objects.filter(
                Q(status=BuildSolutionPDFChore.STARTING)
                | Q(status=BuildSolutionPDFChore.QUEUED)
            ).select_for_update():
                chore.set_as_obsolete()
                if chore.huey_id:
                    queue.revoke_by_id(str(chore.huey_id))
                chore.transition_to_error("never ran: forcibly dequeued")
                N += 1
        return N

    @transaction.atomic
    def get_completed_pdf_files_and_names(self) -> list[tuple[File, str]]:
        """Get list of Files and recommended names of pdf-files of solutions.

        Returns:
            A list of pairs of [django-File, display filename] of the solution pdf.
        """
        return [
            (task.pdf_file, task.display_filename)
            for task in BuildSolutionPDFChore.objects.filter(
                obsolete=False, status=HueyTaskTracker.COMPLETE
            )
        ]

    @transaction.atomic
    def get_zipfly_generator(self, *, chunksize: int = 1024 * 1024) -> zipfly.ZipFly:
        """Return a streaminmg zipfile generator for archive of the solution pdfs.

        Keyword Args:
            chunksize: the size of chunks for the stream.

        Returns:
            The streaming zipfile generator.
        """
        paths = [
            {
                "fs": pdf_file.path,
                "n": f"solutions/{display_filename}",
            }
            for pdf_file, display_filename in self.get_completed_pdf_files_and_names()
        ]

        zfly = zipfly.ZipFly(paths=paths, chunksize=chunksize)
        return zfly.generator()


# The decorated function returns a ``huey.api.Result``
# TODO: investigate "preserve=True" here if we want to wait on them?
@db_task(queue="tasks", context=True)
def huey_build_soln_for_paper(
    paper_number: int,
    *,
    tracker_pk: int,
    _debug_be_flaky: bool = False,
    task: huey.api.Task | None = None,
) -> bool:
    """Build a solution pdf for a single paper, updating the database with progress and resulting PDF.

    Args:
        paper_number: which paper to build solutions for.

    Keyword Args:
        tracker_pk: a key into the database for anyone interested in
            our progress.
        _debug_be_flaky: for debugging, all take a while and some
            percentage will fail.
        task: includes our ID in the Huey process queue.  This kwarg is
            passed by `context=True` in decorator: callers should not
            pass this in!

    Returns:
        True, no meaning, just as per the Huey docs: "if you need to
        block or detect whether a task has finished".
    """
    assert task is not None
    try:
        Paper.objects.get(paper_number=paper_number)
    except Paper.DoesNotExist:
        raise ValueError("No paper with that number") from None

    HueyTaskTracker.transition_to_running(tracker_pk, task.id)

    bss = BuildSolutionService()
    pdf_bytes, soln_pdf_name = bss.assemble_solution_for_paper(
        paper_number, watermark=True
    )

    if _debug_be_flaky:
        for i in range(5):
            print(f"Huey sleep i={i}/4: {task.id}")
            time.sleep(1)
        roll = random.randint(1, 10)
        if roll % 5 == 0:
            raise ValueError(
                f"DEBUG: deliberately failing solution build for {paper_number}"
            )

    with transaction.atomic():
        chore = BuildSolutionPDFChore.objects.select_for_update().get(pk=tracker_pk)
        if not chore.obsolete:
            chore.pdf_file = File(io.BytesIO(pdf_bytes), name=soln_pdf_name)
            chore.display_filename = soln_pdf_name
            chore.save()

    HueyTaskTracker.transition_to_complete(tracker_pk)
    return True
