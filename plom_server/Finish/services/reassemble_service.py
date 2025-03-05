# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Edith Coates
# Copyright (C) 2023-2025 Colin B. Macdonald
# Copyright (C) 2023-2025 Andrew Rechnitzer

from datetime import datetime
from pathlib import Path
import random
import tempfile
import time
from typing import Any

import arrow
import zipfly

from django.core.files import File
from django.db import transaction
from django.db.models import Q
from django.core.exceptions import ObjectDoesNotExist
from django_huey import db_task, get_queue
import huey
import huey.api

from plom.finish.coverPageBuilder import makeCover
from plom.finish.examReassembler import reassemble

from Identify.models import PaperIDTask
from Mark.models import MarkingTask
from Mark.services import MarkingTaskService, MarkingStatsService
from Papers.models import Paper, IDPage, DNMPage, MobilePage
from Papers.services import SpecificationService
from Scan.services import ManageScanService

from ..models import ReassemblePaperChore
from Base.models import HueyTaskTracker

from .student_marks_service import StudentMarkService


class ReassembleService:
    """Class that contains helper functions for sending data to plom-finish."""

    def get_completion_status(self) -> dict[int, tuple[bool, bool, int, datetime]]:
        """Return a dictionary of overall marking completion progress."""
        spreadsheet_data = {}
        papers = Paper.objects.all()
        for paper in papers:
            spreadsheet_data[paper.paper_number] = (
                StudentMarkService().get_paper_status(paper)
            )
        return spreadsheet_data

    def get_legacy_cover_page_info(self, paper: Paper) -> list[list[Any]]:
        """Info needed to build cover page for reassembled paper via legacy command line tool.

        Args:
            paper: a reference to a Paper instance.

        Returns:
            A list of lists ``[[sid, sname], [qi, v, m], ..., [qi, v, m]]``
            where ``qi`` is 1-indexed question index, ``v`` is version and
            ``m`` is mark.
        """
        legacy_cover_page_info: list[list[Any]] = []
        student_info = StudentMarkService.get_paper_id_or_none(paper)
        if student_info:
            student_id, student_name = student_info
        else:
            student_id, student_name = None, None
        legacy_cover_page_info.append([student_id, student_name])

        for i in SpecificationService.get_question_indices():
            version, mark = StudentMarkService().get_question_version_and_mark(paper, i)
            legacy_cover_page_info.append([i, version, mark])

        return legacy_cover_page_info

    def _get_cover_page_info(self, paper: Paper, solution: bool = False) -> list[Any]:
        """Return information needed to build a cover page for a reassembled paper.

        Args:
            paper: a reference to a Paper instance.
            solution (optional): bool, leave out the mark.

        Returns:
            If ``solution`` is True then returns a list of lists
            ``[question_label, version, max_mark]`` for each question.
            Otherwise, ``[question_label, version, mark, max_mark]``.
        """
        sms = StudentMarkService()
        cover_page_info = []

        for i in SpecificationService.get_question_indices():
            question_label = SpecificationService.get_question_label(i)
            max_mark = SpecificationService.get_question_mark(i)
            version, mark = sms.get_question_version_and_mark(paper, i)

            if solution:
                cover_page_info.append([question_label, version, max_mark])
            else:
                cover_page_info.append([question_label, version, mark, max_mark])

        return cover_page_info

    def build_paper_cover_page(
        self, tmpdir: Path, paper: Paper, solution: bool = False
    ) -> Path:
        """Build a cover page for a reassembled PDF or a solution.

        Args:
            tmpdir (pathlib.Path): where to save the coverpage.
            paper: a reference to a Paper instance.
            solution (optional): bool, build coverpage for solutions.

        Returns:
            pathlib.Path: filename of the coverpage.
        """
        tmp = StudentMarkService.get_paper_id_or_none(paper)
        if tmp:
            sid, sname = tmp
        else:
            sid, sname = (None, None)

        cover_page_table_data = self._get_cover_page_info(paper, solution)
        cover_pdf_name = tmpdir / f"cover_{int(paper.paper_number):04}.pdf"
        makeCover(
            cover_page_table_data,
            cover_pdf_name,
            test_num=paper.paper_number,
            info=(sname, sid),
            solution=solution,
            exam_name=SpecificationService.get_longname(),
        )
        return cover_pdf_name

    def get_id_page_image(self, paper: Paper) -> list[dict[str, Any]]:
        """Get the path to image and and rotation for a paper's ID page, if any.

        Args:
            paper: a reference to a Paper instance.

        Returns:
            A list of dictionaries with keys 'filename' and 'rotation'
            giving the path to the image and the rotation angle of the
            image.  If there is no ID page image we get an empty list.
        """
        id_page_obj = IDPage.objects.get(paper=paper)
        if id_page_obj.image:
            return [
                {
                    "filename": id_page_obj.image.image_file.path,
                    "rotation": id_page_obj.image.rotation,
                }
            ]
        else:
            return []

    def get_dnm_page_images(self, paper: Paper) -> list[dict[str, Any]]:
        """Get the path and rotation for a paper's do-not-mark pages.

        Args:
            paper: a reference to a Paper instance.

        Returns:
            List of dicts, each having keys 'filename' and 'rotation'
            giving the path to the image and the rotation angle of the
            image.
        """
        dnm_pages = DNMPage.objects.filter(paper=paper)
        dnm_images = [dnmpage.image for dnmpage in dnm_pages if dnmpage.image]
        return [
            {"filename": img.image_file.path, "rotation": img.rotation}
            for img in dnm_images
        ]

    def _get_seen_but_nonmarked_page_images(self, paper: Paper) -> list[dict[str, Any]]:
        """Get the path and rotation for a paper's pages that weere seen but non-marked.

        TODO: eventually this should look inside the annotations to decide if
        a page was used or not.  For efficiency, perhaps this should should
        be done in the same code that is getting the annotation images.

        Args:
            paper: a reference to a Paper instance.

        Returns:
            List of dicts, each having keys 'filename' and 'rotation'
            giving the path to the image and the rotation angle of the
            image.
        """
        nonmarked = MobilePage.objects.filter(
            paper=paper, question_index=MobilePage.DNM_qidx
        )
        return [
            {"filename": img.image.image_file.path, "rotation": img.image.rotation}
            for img in nonmarked
        ]

    def get_annotation_images(self, paper: Paper) -> list[dict[str, Any]]:
        """Get the paths for a paper's annotation images.

        Args:
            paper: a reference to a Paper instance.

        Returns:
            List of dicts, each having keys 'filename' and 'rotation'
            giving the path to the image and the rotation angle of the
            image.
        """
        marked_pages = []
        mts = MarkingTaskService()
        # note issue #3689 - does not happen here because
        # the question indices from spec are always in
        # the right order
        for qi in SpecificationService.get_question_indices():
            annotation = mts.get_latest_annotation(paper.paper_number, qi)
            marked_pages.append(annotation.image.image.path)
        return marked_pages

    def reassemble_paper(self, paper: Paper, *, outdir: Path | None = None) -> Path:
        """Reassemble a particular paper.

        Args:
            paper: Paper instance to re-assemble.

        Keyword Args:
            outdir: pathlib.Path, the directory to save the PDF
                or a default if omitted.

        Returns:
            pathlib.Path: the full path of the reassembled PDF.
        """
        if outdir is None:
            outdir = Path("reassembled")

        # Do we actually need this given the type-hints... I guess is safer.
        outdir = Path(outdir)
        outdir.mkdir(exist_ok=True)

        paper_id = StudentMarkService.get_paper_id_or_none(paper)
        if not paper_id:
            raise ValueError(
                f"Paper {paper.paper_number} is missing student ID information."
            )
        student_id, student_name = paper_id

        if not StudentMarkService.is_paper_marked(paper):
            raise ValueError(f"Paper {paper.paper_number} is not fully marked.")

        shortname = SpecificationService.get_shortname()
        outname = outdir / f"{shortname}_{student_id}.pdf"

        with tempfile.TemporaryDirectory() as _td:
            tmpdir = Path(_td)
            cover_file = self.build_paper_cover_page(tmpdir, paper)
            id_pages = self.get_id_page_image(paper)
            dnm_pages = self.get_dnm_page_images(paper)
            marked_pages = self.get_annotation_images(paper)
            # Another category: pages seen but not marked.
            # Quick-n-dirty: all those extra pages with empty question_idx
            # later: any page from any other category that has not been included
            # (for example, if Ctrl-R is used to discard a page from every question
            # we could include it here).
            nonmarked = self._get_seen_but_nonmarked_page_images(paper)
            reassemble(
                outname,
                shortname,
                student_id,
                coverfile=cover_file,
                id_images=id_pages,
                marked_pages=marked_pages,
                dnm_images=dnm_pages,
                nonmarked_images=nonmarked,
            )
        return outname

    def get_all_paper_status_for_reassembly(self) -> list[dict[str, Any]]:
        """Get the status information for all papers for reassembly.

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
                "reassembled_status": "",
                "reassembled_time": None,
                "reassembled_time_humanised": None,
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
        for task in ReassemblePaperChore.objects.filter(
            obsolete=False
        ).prefetch_related("paper"):
            status[task.paper.paper_number][
                "reassembled_status"
            ] = task.get_status_display()
            # TODO: is always True
            status[task.paper.paper_number]["obsolete"] = task.obsolete
            if task.status == HueyTaskTracker.COMPLETE:
                status[task.paper.paper_number]["reassembled_time"] = task.last_update
                status[task.paper.paper_number]["reassembled_time_humanised"] = (
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
            if status[pn]["reassembled_time"] and status[pn]["last_update"]:
                if status[pn]["reassembled_time"] < status[pn]["last_update"]:
                    status[pn]["outdated"] = True

        # we used the keys of paper number to build it but now keep only the rows
        return list(status.values())

    def queue_single_paper_reassembly(
        self,
        paper_num: int,
        *,
        build_student_report: bool = True,
        total_score_list: None | list[float] = None,
        question_score_lists: None | dict[int, list[float]] = None,
    ) -> None:
        """Create and queue a huey task to reassemble the given paper.

        If the PDF was already reassembled, it will be first made obsolete.

        Args:
            paper_num: The paper number to re-assemble.

        Keyword Args:
            build_student_report: Whether or not build the student report along with reassembling the paper.
            total_score_list: a list of total scores of all completely marked papers.
            question_score_lists: a dict (keyed by question index) of lists of scores of all marked questions.

        Raises:
            ValueError: no paper with that number, or existing chore.
        """
        try:
            paper = Paper.objects.get(paper_number=paper_num)
        except Paper.DoesNotExist:
            raise ValueError("No paper with that number") from None

        # mark any existing ones obsolete
        try:
            self.reset_single_paper_reassembly(paper_num)
        except ObjectDoesNotExist:
            pass

        # if build_student_report is true, but we dont have the
        # score_list data, then build it here
        if build_student_report:
            if (total_score_list is None) or (question_score_lists is None):
                total_score_list, question_score_lists = (
                    MarkingStatsService().build_report_score_lists()
                )

        with transaction.atomic(durable=True):
            if ReassemblePaperChore.objects.filter(
                paper=paper, obsolete=False
            ).exists():
                raise ValueError(
                    f"There are non-obsolete ReassemblePaperChores for papernum {paper_num}:"
                    " make them obsolete before creating another"
                )
            chore = ReassemblePaperChore.objects.create(
                paper=paper,
                huey_id=None,
                status=ReassemblePaperChore.STARTING,
            )
            chore.save()
            tracker_pk = chore.pk

        res = huey_reassemble_paper(
            paper_num,
            tracker_pk=tracker_pk,
            build_student_report=build_student_report,
            total_score_list=total_score_list,
            question_score_lists=question_score_lists,
            _debug_be_flaky=False,
        )
        print(f"Just enqueued Huey reassembly task id={res.id}")
        HueyTaskTracker.transition_to_queued_or_running(tracker_pk, res.id)

    @transaction.atomic
    def get_single_reassembled_file(self, paper_number: int) -> File:
        """Get the django-file of the reassembled pdf of the given paper.

        Args:
            paper_number (int): The paper number to re-assemble.

        Returns:
            File: the django-File of the reassembled pdf.

        Raises:
            ObjectDoesNotExist: no such paper or reassembly chore, or if
                the reassembly is still in-progress.  TODO: maybe we'd
                like a different exception for the in-progress case.
        """
        chore = ReassemblePaperChore.objects.get(
            paper__paper_number=paper_number,
            obsolete=False,
            status=ReassemblePaperChore.COMPLETE,
        )
        return chore.pdf_file

    @transaction.atomic
    def get_single_student_report(self, paper_number: int) -> File:
        """Get the django-file of the student report pdf of the given paper.

        Args:
            paper_number (int): The paper number.

        Returns:
            File: the django-File of the report pdf.

        Raises:
            ObjectDoesNotExist: no such paper or reassembly chore, or if
                the reassembly is still in-progress.  TODO: maybe we'd
                like a different exception for the in-progress case.
        """
        chore = ReassemblePaperChore.objects.get(
            paper__paper_number=paper_number,
            obsolete=False,
            status=ReassemblePaperChore.COMPLETE,
        )
        return chore.report_pdf_file

    def try_to_cancel_single_queued_chore(self, paper_num: int) -> None:
        """Mark a reassembly chore as obsolete and try to cancel it if queued in Huey.

        Args:
            paper_num: The paper number of the chore to cancel.

        Raises:
            ObjectDoesNotExist: no such paper number or not chore for paper.

        This is a "best-attempt" at catching reassembly chores while they
        are queued.  It might be possible for a Chore to sneak past from the
        "Starting" state.  Already "Running" chores are not effected, although
        they ARE marked as obsolete.
        """
        chore = ReassemblePaperChore.objects.get(
            obsolete=False, paper__paper_number=paper_num
        )
        chore.set_as_obsolete()
        if chore.huey_id:
            queue = get_queue("tasks")
            queue.revoke_by_id(str(chore.huey_id))
        if chore.status in (ReassemblePaperChore.STARTING, ReassemblePaperChore.QUEUED):
            chore.transition_to_error("never ran: forcibly dequeued")

    def try_to_cancel_all_queued_chores(self) -> int:
        """Loop over all not-yet-running chores, marking them obsolete and cancelling (if possible) any in Huey.

        This is a "best-attempt" at catching reassembly chores while they
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
            for chore in ReassemblePaperChore.objects.filter(
                Q(status=ReassemblePaperChore.STARTING)
                | Q(status=ReassemblePaperChore.QUEUED)
            ).select_for_update():
                chore.set_as_obsolete()
                if chore.huey_id:
                    queue.revoke_by_id(str(chore.huey_id))
                chore.transition_to_error("never ran: forcibly dequeued")
                N += 1
        return N

    def reset_single_paper_reassembly(
        self, paper_num: int, *, wait: int | None = None
    ) -> None:
        """Obsolete the reassembly of a paper.

        Args:
            paper_num: The paper number of the reassembly task to reset.

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
        chore = ReassemblePaperChore.objects.filter(
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

    def reset_all_paper_reassembly(self) -> None:
        """Reset all reassembly chores, including completed ones."""
        # TODO: future work for a waiting version, see WIP below?
        wait = None
        # first cancel all queued chores
        self.try_to_cancel_all_queued_chores()
        # any ones that we did not obsolete, we'll get 'em now:
        for chore in ReassemblePaperChore.objects.filter(obsolete=False).all():
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

    def _WIP_reset_all_paper_reassembly(self) -> None:
        """Reset all reassembly tasks and remove any associated pdfs.

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
            for task in ReassemblePaperChore.objects.filter(obsolete=False).all():
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
        for task in ReassemblePaperChore.objects.filter(obsolete=False).all():
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

    def queue_all_paper_reassembly(self, *, build_student_report: bool = True) -> None:
        """Queue the reassembly of all papers that are ready (id'd and marked).

        Keyword Args:
            build_student_report: whether or not to build the student reports at same time.
        """
        if build_student_report:
            total_score_list, question_score_lists = (
                MarkingStatsService().build_report_score_lists()
            )

        # first work out which papers are ready
        for data in self.get_all_paper_status_for_reassembly():
            # check if both id'd and marked
            if not data["identified"] or not data["marked"]:
                continue
            # check if already queued or complete
            # TODO: "Queued" is really `get_status_display` of HueyTaskTracker enum
            if data["reassembled_status"] == "Queued":
                continue
            # TODO: "Complete" is really `get_status_display` of HueyTaskTracker enum
            if data["reassembled_status"] == "Complete" and not data["outdated"]:
                # is complete and not outdated
                continue
            if build_student_report:
                self.queue_single_paper_reassembly(
                    data["paper_num"],
                    build_student_report=True,
                    total_score_list=total_score_list,
                    question_score_lists=question_score_lists,
                )
            else:
                self.queue_single_paper_reassembly(data["paper_num"])

    def how_many_papers_are_mid_reassembly(self) -> int:
        # any chores that are not complete
        return (
            ReassemblePaperChore.objects.exclude(obsolete=True)
            .filter(
                status__in=[
                    ReassemblePaperChore.RUNNING,
                    ReassemblePaperChore.QUEUED,
                    ReassemblePaperChore.STARTING,
                ]
            )
            .count()
        )

    @transaction.atomic
    def get_completed_pdf_files_and_names(
        self, *, first_paper: int | None = None, last_paper: int | None = None
    ) -> list[tuple[File, str]]:
        """Get list of Files and recommended names of pdf-files of reassembled papers that are not obsolete.

        Keyword Args:
            first_paper: filter to get all papers with paper_number greater or equal to this.
            last_paper: filter to get all papers with paper_number less or equal to this.

        Returns:
            A list of pairs [django-File, display filename] of the reassembled pdf.
        """
        query = ReassemblePaperChore.objects.filter(
            obsolete=False, status=HueyTaskTracker.COMPLETE
        )
        if first_paper:
            query = query.filter(paper__paper_number__gte=first_paper)
        if last_paper:
            query = query.filter(paper__paper_number__lte=last_paper)
        return [(task.pdf_file, task.display_filename) for task in query]

    @transaction.atomic
    def get_completed_report_files_and_names(
        self, *, first_paper: int | None = None, last_paper: int | None = None
    ) -> list[tuple[File, str]]:
        """Get list of Files and recommended names of pdf-files of student reports that are not obsolete.

        Keyword Args:
            first_paper: filter to get all papers with paper_number greater or equal to this.
            last_paper: filter to get all papers with paper_number less or equal to this.

        Returns:
            A list of pairs [django-File, display filename] of the reports
        """
        query = ReassemblePaperChore.objects.filter(
            obsolete=False, status=HueyTaskTracker.COMPLETE
        )
        if first_paper:
            query = query.filter(paper__paper_number__gte=first_paper)
        if last_paper:
            query = query.filter(paper__paper_number__lte=last_paper)

        return [(task.report_pdf_file, task.report_display_filename) for task in query]

    @transaction.atomic
    def get_zipfly_generator(
        self,
        short_name: str,
        *,
        first_paper: int | None = None,
        last_paper: int | None = None,
        chunksize: int = 1024 * 1024,
    ):
        """Return a generator that can stream a zipfile of some papers without building in memory.

        Args:
            short_name: TODO: appears to be unused.

        Keyword Args:
            first_paper: optionally grab papers greater than or equal
                to this paper number.  Omit or `None` for no restriction.
            last_paper: optionally grab papers less than or equal to
                this number.  Omit or `None` for no restriction.
            chunksize: a parameter related to the building of the zipfile.

        Returns:
            Some sort of generator for the zipfile streamer.

        Raises:
            ValueError: if there are no reassembled papers in the requested range.
        """
        paths = [
            {
                "fs": pdf_file.path,
                "n": f"reassembled/{display_filename}",
            }
            for pdf_file, display_filename in self.get_completed_pdf_files_and_names(
                first_paper=first_paper, last_paper=last_paper
            )
        ]
        # report_paths = [
        #     {
        #         "fs": report_pdf_file.path,
        #         "n": f"student_reports/{report_display_filename}",
        #     }
        #     for report_pdf_file, report_display_filename in self.get_completed_report_files_and_names()
        # ]

        if not paths:
            rng1 = f"{first_paper} <= " if first_paper is not None else ""
            rng2 = f" <= {last_paper}" if last_paper is not None else ""
            if rng1 or rng2:
                rng_msg = " satisfying " + rng1 + "paper_number" + rng2
            else:
                rng_msg = ""
            raise ValueError("There are no reassembled papers" + rng_msg)
        # zfly = zipfly.ZipFly(paths=paths + report_paths, chunksize=chunksize)
        zfly = zipfly.ZipFly(paths=paths, chunksize=chunksize)
        return zfly.generator()


# The decorated function returns a ``huey.api.Result``
# TODO: investigate "preserve=True" here if we want to wait on them?
@db_task(queue="tasks", context=True)
def huey_reassemble_paper(
    paper_number: int,
    *,
    tracker_pk: int,
    build_student_report: bool = True,
    total_score_list: None | list[float] = None,
    question_score_lists: None | dict[int, list[float]] = None,
    _debug_be_flaky: bool = False,
    task: huey.api.Task | None = None,
) -> bool:
    """Reassemble a single paper, updating the database with progress and resulting PDF.

    Args:
        paper_number: which paper to reassemble.

    Keyword Args:
        tracker_pk: a key into the database for anyone interested in
            our progress.
        build_student_report: whether or not to build the student report at the same time.
        total_score_list: a list of total scores of all completely marked papers.
        question_score_lists: a dict (keyed by question index) of lists of scores of all marked questions.
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
        paper_obj = Paper.objects.get(paper_number=paper_number)
    except Paper.DoesNotExist:
        raise ValueError("No paper with that number") from None

    HueyTaskTracker.transition_to_running(tracker_pk, task.id)

    from .build_student_report_service import BuildStudentReportService

    with tempfile.TemporaryDirectory() as tempdir:
        save_path = ReassembleService().reassemble_paper(
            paper_obj, outdir=Path(tempdir)
        )
        report_data = BuildStudentReportService().build_brief_report(
            paper_number, total_score_list, question_score_lists
        )
        # save the report data to file in tempdir - TODO can we do this all in memory?
        report_path = Path(tempdir) / report_data["filename"]
        with report_path.open("wb") as fh:
            fh.write(report_data["bytes"])

        if _debug_be_flaky:
            for i in range(5):
                print(f"Huey sleep i={i}/4: {task.id}")
                time.sleep(1)
            roll = random.randint(1, 10)
            if roll % 5 == 0:
                raise ValueError(
                    f"DEBUG: deliberately failing creation of reassembly {paper_number}"
                )

        with transaction.atomic():
            chore = ReassemblePaperChore.objects.select_for_update().get(pk=tracker_pk)
            if not chore.obsolete:
                with save_path.open("rb") as f:
                    chore.pdf_file = File(f, name=save_path.name)
                    chore.display_filename = save_path.name
                    chore.save()
                with report_path.open("rb") as f2:
                    chore.report_pdf_file = File(f2, name=report_path.name)
                    chore.report_display_filename = report_path.name
                    chore.save()

    HueyTaskTracker.transition_to_complete(tracker_pk)
    return True
