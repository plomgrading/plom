# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Edith Coates
# Copyright (C) 2023 Colin B. Macdonald
# Copyright (C) 2023 Andrew Rechnitzer

import arrow
from datetime import datetime
from pathlib import Path
import random
import tempfile
import time
from typing import Any, Dict, List, Optional
import zipfly

from django.conf import settings
from django.core.files import File
from django.db import transaction
from django.utils import timezone
from django_huey import db_task, get_queue

from plom.finish.coverPageBuilder import makeCover
from plom.finish.examReassembler import reassemble

from Identify.models import PaperIDTask
from Mark.models import MarkingTask, Annotation
from Mark.services import MarkingTaskService
from Papers.models import Paper, IDPage, DNMPage
from Papers.services import SpecificationService, PaperInfoService
from Progress.services import ManageScanService

from ..models import ReassembleHueyTaskTracker
from Base.models import HueyTaskTracker


class ReassembleService:
    """Class that contains helper functions for sending data to plom-finish."""

    base_dir = settings.MEDIA_ROOT
    reassemble_dir = base_dir / "reassemble"

    def is_paper_marked(self, paper: Paper) -> bool:
        """Return True if all of the marking tasks are completed.

        Args:
            paper: a reference to a Paper instance

        Returns:
            bool: True when all questions in the given paper are marked.
        """
        paper_tasks = MarkingTask.objects.filter(paper=paper)
        n_completed_tasks = paper_tasks.filter(status=MarkingTask.COMPLETE).count()
        n_out_of_date_tasks = paper_tasks.filter(status=MarkingTask.OUT_OF_DATE).count()
        n_all_tasks = paper_tasks.count()
        n_questions = SpecificationService.get_n_questions()
        return (n_completed_tasks == n_questions) and (
            n_completed_tasks + n_out_of_date_tasks == n_all_tasks
        )

    def are_all_papers_marked(self) -> bool:
        """Return True if all of the papers that have a task are marked."""
        papers = Paper.objects.exclude(markingtask__isnull=True)

        for paper in papers:
            if not self.is_paper_marked(paper):
                return False
        return True

    def get_n_questions_marked(self, paper: Paper) -> int:
        """Return the number of questions that are marked in a paper.

        Args:
            paper: a reference to a Paper instance
        """
        n_questions = SpecificationService.get_n_questions()
        n_marked = 0
        for i in range(1, n_questions + 1):
            question_number_tasks = MarkingTask.objects.filter(
                paper=paper, question_number=i, status=MarkingTask.COMPLETE
            )
            if question_number_tasks.count() == 1:
                n_marked += 1
        return n_marked

    def get_last_updated_timestamp(self, paper: Paper) -> datetime:
        """Return the latest update timestamp from the IDActions or Annotations.

        Args:
            paper: a reference to a Paper instance

        Returns:
            datetime: the time of the latest update to any task in the paper.
            WARNING: If paper is not id'd and not marked then returns the current
            time.
        """
        try:
            paper_id_task = PaperIDTask.objects.exclude(
                status=PaperIDTask.OUT_OF_DATE
            ).get(paper=paper)
            last_id_time = paper_id_task.latest_action.time
        except PaperIDTask.DoesNotExist:
            last_id_time = None

        if self.is_paper_marked(paper):
            last_annotation_time = (
                Annotation.objects.exclude(task__status=PaperIDTask.OUT_OF_DATE)
                .filter(task__paper=paper)
                .order_by("-time_of_last_update")
                .first()
                .time_of_last_update
            )
        else:
            last_annotation_time = None

        if last_id_time and last_annotation_time:
            return max(last_id_time, last_annotation_time)
        elif last_id_time:
            return last_id_time
        elif last_annotation_time:
            return last_annotation_time
        else:
            # TODO: default to the current date for the time being
            return timezone.now()

    def get_paper_id_or_none(self, paper: Paper) -> Optional[tuple[str, str]]:
        """Return a tuple of (student ID, student name) if the paper has been identified. Otherwise, return None.

        Args:
            paper: a reference to a Paper instance

        Returns:
            a tuple (str, str) or None
        """
        try:
            task = PaperIDTask.objects.filter(
                paper=paper, status=PaperIDTask.COMPLETE
            ).get()
        except PaperIDTask.DoesNotExist:
            return None
        action = task.latest_action
        return action.student_id, action.student_name

    def get_question_data(
        self, paper: Paper, question_number: int
    ) -> tuple[int, Optional[int]]:
        """For a given question, return the test's question version and score.

        Args:
            paper: a reference to a Paper instance
            question_number: int, question index

        Returns:
            tuple (int, int or None): question version and score

        Raises:
            ObjectDoesNotExist: no such marking task, either b/c the paper
            does not exist or the question does not exist for that paper.
        """
        version = PaperInfoService().get_version_from_paper_question(
            paper.paper_number, question_number
        )
        if self.is_paper_marked(paper):
            annotation = MarkingTaskService().get_latest_annotation(
                paper.paper_number, question_number
            )
            mark = annotation.score
        else:
            mark = None
        return version, mark

    def paper_spreadsheet_dict(self, paper: Paper) -> Dict[str, Any]:
        """Return a dictionary representing a paper for the reassembly spreadsheet.

        Args:
            paper: a reference to a Paper instance
        """
        paper_dict: Dict[str, Any] = {}

        paper_id_info = self.get_paper_id_or_none(paper)
        if paper_id_info:
            student_id, student_name = paper_id_info
            paper_dict["sid"] = student_id
            paper_dict["sname"] = student_name
        else:
            paper_dict["sid"] = ""
            paper_dict["sname"] = ""
        paper_dict["identified"] = paper_id_info is not None

        n_questions = SpecificationService.get_n_questions()
        paper_marked = self.is_paper_marked(paper)
        for i in range(1, n_questions + 1):
            version, mark = self.get_question_data(paper, i)
            paper_dict[f"q{i}m"] = mark
            paper_dict[f"q{i}v"] = version
        paper_dict["marked"] = paper_marked

        paper_dict["last_update"] = self.get_last_updated_timestamp(paper)
        return paper_dict

    def get_paper_status(self, paper: Paper) -> tuple[bool, bool, int, datetime]:
        """Return a list of [scanned?, identified?, n questions marked, time of last update] for a given paper.

        Args:
            paper: reference to a Paper object

        Returns:
            tuple of [bool, bool, int, datetime]
        """
        paper_id_info = self.get_paper_id_or_none(paper)
        is_id = paper_id_info is not None
        complete_paper_keys = ManageScanService().get_all_completed_test_papers().keys()
        is_scanned = paper.paper_number in complete_paper_keys
        n_marked = self.get_n_questions_marked(paper)
        last_modified = self.get_last_updated_timestamp(paper)

        return (is_scanned, is_id, n_marked, last_modified)

    def get_spreadsheet_data(self) -> Dict[str, Any]:
        """Return a dictionary with all of the required data for a reassembly spreadsheet."""
        spreadsheet_data = {}
        papers = Paper.objects.all()
        for paper in papers:
            spreadsheet_data[paper.paper_number] = self.paper_spreadsheet_dict(paper)
        return spreadsheet_data

    def get_identified_papers(self) -> Dict[str, List[str]]:
        """Return a dictionary with all of the identified papers and their names and IDs.

        Returns:
            dictionary: keys are paper numbers, values are a list of [str, str]
        """
        spreadsheet_data = {}
        papers = Paper.objects.all()
        for paper in papers:
            paper_id_info = self.get_paper_id_or_none(paper)
            if paper_id_info:
                student_id, student_name = paper_id_info
                spreadsheet_data[paper.paper_number] = [student_id, student_name]
        return spreadsheet_data

    def get_completion_status(self) -> Dict[int, tuple[bool, bool, int, datetime]]:
        """Return a dictionary of overall test completion progress."""
        spreadsheet_data = {}
        papers = Paper.objects.all()
        for paper in papers:
            spreadsheet_data[paper.paper_number] = self.get_paper_status(paper)
        return spreadsheet_data

    def get_cover_page_info(self, paper: Paper, solution: bool = False) -> List[Any]:
        """Return information needed to build a cover page for a reassembled test.

        Args:
            paper: a reference to a Paper instance
            solution (optional): bool, leave out the max possible mark.

        Returns:
            If ``solution`` is True then returns a list of lists
            ``[question_label, version, max_mark]`` for each question.
            Otherwise, ``[question_label, version, mark, max_mark]``.
        """
        cover_page_info = []

        n_questions = SpecificationService.get_n_questions()
        for i in range(1, n_questions + 1):
            question_label = SpecificationService.get_question_label(i)
            max_mark = SpecificationService.get_question_mark(i)
            version, mark = self.get_question_data(paper, i)

            if solution:
                cover_page_info.append([question_label, version, max_mark])
            else:
                cover_page_info.append([question_label, version, mark, max_mark])

        return cover_page_info

    def build_paper_cover_page(
        self, tmpdir, paper: Paper, solution: bool = False
    ) -> Path:
        """Build a cover page for a reassembled PDF or a solution.

        Args:
            tmpdir (pathlib.Path): where to save the coverpage.
            paper: a reference to a Paper instance.
            solution (optional): bool, build coverpage for solutions.

        Returns:
            pathlib.Path: filename of the coverpage.
        """
        # some annoying work here to handle casting None to (None, None) while keeping mypy happy
        paper_id: Optional[
            tuple[Optional[str], Optional[str]]
        ] = self.get_paper_id_or_none(paper)
        if not paper_id:
            paper_id = (None, None)

        cover_page_info = self.get_cover_page_info(paper, solution)
        cover_name = tmpdir / f"cover_{int(paper.paper_number):04}.pdf"
        makeCover(
            cover_page_info,
            cover_name,
            test_num=paper.paper_number,
            info=paper_id,
            solution=solution,
            exam_name=SpecificationService.get_longname(),
        )
        return cover_name

    def get_id_page_image(self, paper: Paper) -> Dict[str, Any]:
        """Get the path and rotation for a paper's ID page.

        Args:
            paper: a reference to a Paper instance.

        Returns:
            Dict: with keys 'filename' and 'rotation' giving the path to the image and the rotation angle of the image.

        """
        id_page_image = IDPage.objects.get(paper=paper).image
        return {
            "filename": id_page_image.image_file.path,
            "rotation": id_page_image.rotation,
        }

    def get_dnm_page_images(self, paper: Paper) -> List[Dict[str, Any]]:
        """Get the path and rotation for a paper's do-not-mark pages.

        Args:
            paper: a reference to a Paper instance.

        Returns:
            List of Dict: Each dict has with keys 'filename' and 'rotation' giving the path to the image and the rotation angle of the image.

        """
        dnm_pages = DNMPage.objects.filter(paper=paper)
        dnm_images = [dnmpage.image for dnmpage in dnm_pages]
        return [
            {"filename": img.image_file.path, "rotation": img.rotation}
            for img in dnm_images
        ]

    def get_annotation_images(self, paper: Paper) -> List[Dict[str, Any]]:
        """Get the paths for a paper's annotation images.

        Args:
            paper: a reference to a Paper instance.

        Returns:
            List of Dict: Each dict has with keys 'filename' and 'rotation' giving the path to the image and the rotation angle of the image.
        """
        n_questions = SpecificationService.get_n_questions()
        marked_pages = []

        mts = MarkingTaskService()
        for i in range(1, n_questions + 1):
            annotation = mts.get_latest_annotation(paper.paper_number, i)
            marked_pages.append(annotation.image.image.path)

        return marked_pages

    def reassemble_paper(self, paper: Paper, outdir: Optional[Path]) -> Path:
        """Reassemble a single test paper.

        Args:
            paper: Paper instance to re-assemble.
            outdir (optional): pathlib.Path, the directory to save the test PDF.

        Returns:
            pathlib.Path: the full path of the reassembled test PDF.
        """
        if outdir is None:
            outdir = Path("reassembled")

        # Do we actually need this given the type-hints... I guess is safer.
        outdir = Path(outdir)
        outdir.mkdir(exist_ok=True)

        paper_id = self.get_paper_id_or_none(paper)
        if not paper_id:
            raise ValueError(
                f"Paper {paper.paper_number} is missing student ID information."
            )
        student_id, student_name = paper_id

        if not self.is_paper_marked(paper):
            raise ValueError(f"Paper {paper.paper_number} is not fully marked.")

        shortname = SpecificationService.get_shortname()
        outname = outdir / f"{shortname}_{student_id}.pdf"

        with tempfile.TemporaryDirectory() as _td:
            tmpdir = Path(_td)
            cover_file = self.build_paper_cover_page(tmpdir, paper)
            id_pages = [self.get_id_page_image(paper)]  # cast to a list.
            dnm_pages = self.get_dnm_page_images(paper)
            marked_pages = self.get_annotation_images(paper)
            reassemble(
                outname,
                shortname,
                student_id,
                cover_file,
                id_pages,
                marked_pages,
                dnm_pages,
            )
        return outname

    def get_all_paper_status_for_reassembly(self) -> List[Dict[str, Any]]:
        """Get the status information for all papers for reassembly.

        Returns:
            List of dicts representing each row of the data.
        """
        status: Dict[str, Any] = {}
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
                "reassembled_status": None,
                "reassembled_time": None,
                "reassembled_time_humanised": None,
                "outdated": False,
            }
        mss = ManageScanService()
        number_of_questions = SpecificationService.get_n_questions()

        for pn in mss.get_all_completed_test_papers():
            status[pn]["scanned"] = True

        def latest_update(time_a: Optional[datetime], time_b: datetime) -> datetime:
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

        for task in ReassembleHueyTaskTracker.objects.all().prefetch_related("paper"):
            status[task.paper.paper_number][
                "reassembled_status"
            ] = task.get_status_display()
            if task.status == HueyTaskTracker.COMPLETE:
                status[task.paper.paper_number]["reassembled_time"] = task.last_update
                status[task.paper.paper_number][
                    "reassembled_time_humanised"
                ] = arrow.get(task.last_update).humanize()

        # do last round of updates
        for pn in status:
            if status[pn]["number_marked"] == number_of_questions:
                status[pn]["marked"] = True
            if status[pn]["last_update"]:
                status[pn]["last_update_humanised"] = arrow.get(
                    status[pn]["last_update"]
                ).humanize()
            if status[pn]["reassembled_time"]:
                if status[pn]["reassembled_time"] < status[pn]["last_update"]:
                    status[pn]["outdated"] = True

        # we used the keys of paper number to build it but now keep only the rows
        return list(status.values())

    def create_all_reassembly_tasks(self):
        """Create all the ReassembleHueyTaskTrackers, and save to the database without sending them to Huey."""
        self.reassemble_dir.mkdir(exist_ok=True)
        for paper_obj in Paper.objects.all():
            ReassembleHueyTaskTracker.objects.create(
                paper=paper_obj, huey_id=None, status=HueyTaskTracker.TO_DO
            )

    def queue_single_paper_reassembly(self, paper_number: int) -> None:
        """Create and queue a huey task to reassemble the given paper.

        Args:
            paper_number (int): The paper number to re-assemble.
        """
        try:
            paper_obj = Paper.objects.get(paper_number=paper_number)
        except Paper.DoesNotExist:
            raise ValueError("No paper with that number") from None

        with transaction.atomic(durable=True):
            tr = paper_obj.reassemblehueytasktracker
            tr.reset_to_do()
            tr.transition_to_starting()
            tracker_pk = tr.pk

        res = huey_reassemble_paper(
            paper_number, tracker_pk=tracker_pk, _debug_be_flaky=False
        )
        print(f"Just enqueued Huey reassembly task id={res.id}")

        with transaction.atomic(durable=True):
            tr = HueyTaskTracker.objects.get(pk=tracker_pk)
            tr.transition_to_queued_or_running(res.id)

    @transaction.atomic
    def get_single_reassembled_file(self, paper_number: int) -> File:
        """Get the django-file of the reassembled pdf of the given paper.

        Args:
            paper_number (int): The paper number to re-assemble.

        Returns:
            File: the django-File of the reassembled pdf.
        """
        try:
            paper_obj = Paper.objects.get(paper_number=paper_number)
        except Paper.DoesNotExist:
            raise ValueError("No paper with that number") from None
        task = paper_obj.reassemblehueytasktracker
        return task.pdf_file

    def reset_single_paper_reassembly(self, paper_number: int) -> None:
        """Reset to TO_DO the reassembly task of the given paper and remove pdf if it exists.

        Args:
            paper_number: The paper number of the reassembly task to reset.

        Raises:
            RuntimeError: any running tasks.  For now, just wait before
                clicking the "reset all" button!

        This is a "best-attempt" at catching reassembly chores while they
        are queued.

        TODO: this may be susceptible to race conditions, so I do not think
        it is guaranteed to block a huey task from running.
        """
        try:
            paper_obj = Paper.objects.get(paper_number=paper_number)
        except Paper.DoesNotExist:
            raise ValueError("No paper with that number") from None

        queue = get_queue("tasks")
        task = paper_obj.reassemblehueytasktracker
        if task.status == HueyTaskTracker.QUEUED:
            queue.revoke_by_id(str(task.huey_id))
        if task.status == HueyTaskTracker.RUNNING:
            raise RuntimeError(f"Task running {task.huey_id}, cannot reset")
            return
        task.reset_to_do()

    def reset_all_paper_reassembly(self) -> None:
        """Reset to TO_DO all reassembly tasks and remove any associated pdfs.

        This tries to somewhat gracefully ("like an eagle...piloting a blimp")
        revoke queued tasks, wait for running tasks, etc.

        Raises:
            RuntimeError: any running tasks.  For now, just wait before
                clicking the "reset all" button!
        """
        queue = get_queue("tasks")

        for task in ReassembleHueyTaskTracker.objects.exclude(
            status=HueyTaskTracker.TO_DO,
        ).all():
            if task.status == HueyTaskTracker.QUEUED:
                queue.revoke_by_id(str(task.huey_id))
            if task.status == HueyTaskTracker.RUNNING:
                raise RuntimeError(f"Task running {task.huey_id}, cannot reset")
            task.reset_to_do()

    def WIP_reset_single_paper_reassembly(
        self, paper_number: int, *, wait: int = 10
    ) -> None:
        """Reset to TO_DO the reassembly task of the given paper and remove pdf if it exists.

        Args:
            paper_number: The paper number of the reassembly task to reset.

        Keyword Args:
            wait: how many seconds to wait before timing out for running
                tasks (default 10 seconds).

        Raises:
            HueyException: timed out waiting for result.

        TODO: this may be susceptible to race conditions, so I do not think
        it is guaranteed to block a huey task from running.
        """
        try:
            paper_obj = Paper.objects.get(paper_number=paper_number)
        except Paper.DoesNotExist:
            raise ValueError("No paper with that number") from None

        queue = get_queue("tasks")
        task = paper_obj.reassemblehueytasktracker
        # if the task is queued then remove it from the queue
        if task.status == HueyTaskTracker.QUEUED:
            queue.revoke_by_id(str(task.huey_id))
        if task.status == HueyTaskTracker.RUNNING:
            print(f"Task running: {task.huey_id}, we will wait for {wait}s...")
            r = queue.result(
                str(task.huey_id), blocking=True, timeout=wait, preserve=True
            )
            print(f"The running task {task.huey_id} has finished, and returned {r}")
        task.reset_to_do()

    def WIP_reset_all_paper_reassembly(self) -> None:
        """Reset to TO_DO all reassembly tasks and remove any associated pdfs.

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

        # Regarding cost: b/c we filter excluding TO_DO, only the first loop is likely
        # to be significant (in the common case when many things are QUEUED or STARTING).
        while tries > 0:
            how_many_running = 0
            for task in ReassembleHueyTaskTracker.objects.exclude(
                status=HueyTaskTracker.TO_DO
            ).all():
                if task.status == HueyTaskTracker.QUEUED:
                    queue.revoke_by_id(str(task.huey_id))
                elif task.status == HueyTaskTracker.RUNNING:
                    how_many_running += 1
                    print(f"There is a running task: {task.huey_id}")
                else:
                    task.reset_to_do()
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
        for task in ReassembleHueyTaskTracker.objects.exclude(
            status=HueyTaskTracker.TO_DO
        ).all():
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
            task.reset_to_do()

    def queue_all_paper_reassembly(self) -> None:
        """Queue the reassembly of all papers that are ready (id'd and marked)."""
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
            self.queue_single_paper_reassembly(data["paper_num"])

    @transaction.atomic
    def get_completed_pdf_files(self) -> List[File]:
        """Get list of paths of pdf-files of completed (built) tests papers.

        Returns:
            A list of django-Files of the reassembled pdf.
        """
        return [
            task.pdf_file
            for task in ReassembleHueyTaskTracker.objects.filter(
                status=HueyTaskTracker.COMPLETE
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
# TODO: investigate "preserver=True" here if we want to wait on them?
@db_task(queue="tasks", context=True)
def huey_reassemble_paper(
    paper_number: int, *, tracker_pk: int, task=None, _debug_be_flaky: bool = False
) -> bool:
    """Reassemble a single paper, updating the database with progress and resulting PDF.

    Args:
        paper_number: which paper to reassemble.

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

    with transaction.atomic():
        HueyTaskTracker.objects.get(pk=tracker_pk).transition_to_running(task.id)

    reas = ReassembleService()
    with tempfile.TemporaryDirectory() as tempdir:
        save_path = reas.reassemble_paper(paper_obj, Path(tempdir))

        if _debug_be_flaky:
            for i in range(5):
                print(f"Huey sleep i={i}/4: {task.id}")
                time.sleep(1)
            roll = random.randint(1, 10)
            if roll % 5 == 0:
                raise ValueError(
                    f"DEBUG: deliberately failing creation of reassembly {paper_number}"
                )

        with save_path.open("rb") as f:
            with transaction.atomic():
                # TODO: unclear to me if we need to re-get the task
                tr = ReassembleHueyTaskTracker.objects.get(pk=tracker_pk)
                # TODO: IMHO, the pdf file does not belong in the Tracker obj
                # TODO: I think we should have deleted it before restarting so this isn't needed
                # delete any old file if it exists
                if tr.pdf_file:
                    tr.pdf_file.delete()
                # save the new one.
                tr.pdf_file = File(f, name=save_path.name)
                tr.transition_to_complete()
    return True
