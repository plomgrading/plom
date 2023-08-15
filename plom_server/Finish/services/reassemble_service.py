# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Edith Coates
# Copyright (C) 2023 Colin B. Macdonald

import arrow
from pathlib import Path
import tempfile
import zipfly

from plom.finish.coverPageBuilder import makeCover
from plom.finish.examReassembler import reassemble


from django.conf import settings
from django.core.files import File
from django.db import transaction
from django.utils import timezone

from django_huey import db_task, get_queue

from Identify.models import PaperIDTask, PaperIDAction
from Mark.models import MarkingTask, Annotation
from Mark.services import MarkingTaskService
from Papers.models import Paper, IDPage, DNMPage
from Papers.services import SpecificationService, PaperInfoService
from Progress.services import ManageScanService

from ..models import ReassembleTask


class ReassembleService:
    """Class that contains helper functions for sending data to plom-finish."""

    base_dir = settings.MEDIA_ROOT
    reassemble_dir = base_dir / "reassemble"

    def is_paper_marked(self, paper):
        """Return True if all of the marking tasks are completed.

        Args:
            paper: a reference to a Paper instance
        """
        paper_tasks = MarkingTask.objects.filter(paper=paper)
        completed_tasks = paper_tasks.filter(status=MarkingTask.COMPLETE)
        ood_tasks = paper_tasks.filter(status=MarkingTask.OUT_OF_DATE)
        n_questions = SpecificationService.get_n_questions()
        return (
            completed_tasks.count() == n_questions
            and completed_tasks.count() + ood_tasks.count() == paper_tasks.count()
        )

    def are_all_papers_marked(self) -> bool:
        """Return True if all of the papers that have a task are marked."""
        papers = Paper.objects.exclude(markingtask__isnull=True)

        for paper in papers:
            if not self.is_paper_marked(paper):
                return False
        return True

    def get_n_questions_marked(self, paper):
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

    def get_last_updated_timestamp(self, paper):
        """Return the latest update timestamp from the IDActions or Annotations.

        Args:
            paper: a reference to a Paper instance
        """
        if self.get_paper_id_or_none(paper):
            paper_id_task = PaperIDTask.objects.get(paper=paper)
            paper_id_actions = PaperIDAction.objects.filter(task=paper_id_task)
            latest_action_instance = paper_id_actions.order_by("-time").first()
            latest_action = latest_action_instance.time
        else:
            latest_action = None

        if self.is_paper_marked(paper):
            paper_annotations = Annotation.objects.filter(task__paper=paper)
            latest_annotation_instance = paper_annotations.order_by(
                "-time_of_last_update"
            ).first()
            latest_annotation = latest_annotation_instance.time_of_last_update
        else:
            latest_annotation = None

        if latest_action and latest_annotation:
            return max(latest_annotation, latest_action)
        elif latest_action:
            return latest_action
        elif latest_annotation:
            return latest_annotation
        else:
            # TODO: default to the current date for the time being
            return timezone.now()

    def get_paper_id_or_none(self, paper):
        """Return a tuple of (student ID, student name) if the paper has been identified. Otherwise, return None.

        Args:
            paper: a reference to a Paper instance

        Returns:
            a tuple (str, str) or None
        """
        paper_task = PaperIDTask.objects.filter(paper=paper).order_by("-time")
        if paper_task.count() == 0:
            return None
        latest_task = paper_task.first()
        if latest_task.status != PaperIDTask.COMPLETE:
            return None
        action = PaperIDAction.objects.get(task=latest_task)
        return action.student_id, action.student_name

    def get_question_data(self, paper, question_number):
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

    def paper_spreadsheet_dict(self, paper):
        """Return a dictionary representing a paper for the reassembly spreadsheet.

        Args:
            paper: a reference to a Paper instance
        """
        paper_dict = {}

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

    def get_paper_status(self, paper):
        """Return a list of [scanned?, identified?, n questions marked, time of last update] for a given paper.

        Args:
            paper: reference to a Paper object

        Returns:
            list of [bool, bool, int, datetime]
        """
        paper_id_info = self.get_paper_id_or_none(paper)
        is_id = paper_id_info is not None
        complete_paper_keys = ManageScanService().get_all_completed_test_papers().keys()
        is_scanned = paper.paper_number in complete_paper_keys
        n_marked = self.get_n_questions_marked(paper)
        last_modified = self.get_last_updated_timestamp(paper)

        return [is_scanned, is_id, n_marked, is_scanned, last_modified]

    def get_spreadsheet_data(self):
        """Return a dictionary with all of the required data for a reassembly spreadsheet."""
        spreadsheet_data = {}
        papers = Paper.objects.all()
        for paper in papers:
            spreadsheet_data[paper.paper_number] = self.paper_spreadsheet_dict(paper)
        return spreadsheet_data

    def get_identified_papers(self):
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

    def get_completion_status(self):
        """Return a dictionary of overall test completion progress."""
        spreadsheet_data = {}
        papers = Paper.objects.all()
        for paper in papers:
            spreadsheet_data[paper.paper_number] = self.get_paper_status(paper)
        return spreadsheet_data

    def get_cover_page_info(self, paper, solution=False):
        """Return information needed to build a cover page for a reassembled test.

        Args:
            paper: a reference to a Paper instance
            solution (optional): bool, leave out the max possible mark.
        """
        cover_page_info = []

        spec_service = SpecificationService
        n_questions = spec_service.get_n_questions()
        for i in range(1, n_questions + 1):
            question_label = spec_service.get_question_label(i)
            max_mark = spec_service.get_question_mark(i)
            version, mark = self.get_question_data(paper, i)

            if solution:
                cover_page_info.append([question_label, version, max_mark])
            else:
                cover_page_info.append([question_label, version, mark, max_mark])

        return cover_page_info

    def build_paper_cover_page(self, tmpdir, paper, solution=False):
        """Build a cover page for a reassembled PDF or a solution.

        Args:
            tmpdir (pathlib.Path): where to save the coverpage.
            paper: a reference to a Paper instance.
            solution (optional): bool, build coverpage for solutions.

        Returns:
            pathlib.Path: filename of the coverpage.
        """
        paper_id = self.get_paper_id_or_none(paper)
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

    def get_id_page_image(self, paper):
        """Get the path and rotation for a paper's ID page."""
        id_page_image = IDPage.objects.get(paper=paper).image
        return [
            {
                "filename": id_page_image.image_file.path,
                "rotation": id_page_image.rotation,
            }
        ]

    def get_dnm_page_images(self, paper):
        """Get the path and rotation for a paper's do-not-mark pages."""
        dnm_pages = DNMPage.objects.filter(paper=paper)
        dnm_images = [dnmpage.image for dnmpage in dnm_pages]
        return [
            {"filename": img.image_file.path, "rotation": img.rotation}
            for img in dnm_images
        ]

    def get_annotation_images(self, paper):
        """Get the paths for a paper's annotation images."""
        n_questions = SpecificationService.get_n_questions()
        marked_pages = []

        mts = MarkingTaskService()
        for i in range(1, n_questions + 1):
            annotation = mts.get_latest_annotation(paper.paper_number, i)
            marked_pages.append(annotation.image.path)

        return marked_pages

    def reassemble_paper(self, paper, outdir):
        """Reassemble a single test paper.

        Args:
            paper: Paper instance to re-assemble.
            outdir (optional): pathlib.Path, the directory to save the test PDF.

        Returns:
            pathlib.Path: the full path of the reassembled test PDF.
        """
        if outdir is None:
            outdir = "reassembled"

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
            id_pages = self.get_id_page_image(paper)
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

    def alt_get_all_paper_status(self):
        status = {}
        all_papers = Paper.objects.all()
        for paper in all_papers:
            status[paper.paper_number] = {
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

        def latest_update(time_a, time_b):
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

        for task in ReassembleTask.objects.all().prefetch_related("paper"):
            status[task.paper.paper_number][
                "reassembled_status"
            ] = task.get_status_display()
            if task.status == ReassembleTask.COMPLETE:
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
        return status

    def create_all_reassembly_tasks(self):
        """Create all the ReassembleTasks, and save to the database without sending them to Huey."""
        self.reassemble_dir.mkdir(exist_ok=True)
        for paper_obj in Paper.objects.all():
            ReassembleTask.objects.create(
                paper=paper_obj, huey_id=None, status=ReassembleTask.TO_DO
            )

    @transaction.atomic
    def queue_single_paper_reassembly(self, paper_number):
        try:
            paper_obj = Paper.objects.get(paper_number=paper_number)
        except Paper.DoesNotExist:
            raise ValueError("No paper with that number")

        task = paper_obj.reassembletask
        pdf_build = huey_reassemble_paper(paper_number)
        task.huey_id = pdf_build.id
        task.status = ReassembleTask.QUEUED
        task.save()

    @transaction.atomic
    def get_single_reassembled_file(self, paper_number):
        try:
            paper_obj = Paper.objects.get(paper_number=paper_number)
        except Paper.DoesNotExist:
            raise ValueError("No paper with that number")
        task = paper_obj.reassembletask
        return task.pdf_file

    @transaction.atomic
    def reset_single_paper_reassembly(self, paper_number):
        try:
            paper_obj = Paper.objects.get(paper_number=paper_number)
        except Paper.DoesNotExist:
            raise ValueError("No paper with that number")

        task = paper_obj.reassembletask
        # if the task is queued then remove it from the queue
        if task.status == ReassembleTask.QUEUED:
            queue = get_queue("tasks")
            queue.revoke_by_id(task.huey_id)
        # if there is a file then remove it
        if task.pdf_file:
            task.pdf_file.delete()

        task.huey_id = None
        task.status = ReassembleTask.TO_DO
        task.save()

    @transaction.atomic
    def reset_all_paper_reassembly(self):
        queue = get_queue("tasks")
        for task in ReassembleTask.objects.exclude(status=ReassembleTask.TO_DO).all():
            # if the task is queued then remove it from the queue
            if task.status == ReassembleTask.QUEUED:
                queue.revoke_by_id(task.huey_id)
            # if there is a file then delete it.
            if task.pdf_file:
                task.pdf_file.delete()
            task.huey_id = None
            task.status = ReassembleTask.TO_DO
            task.save()

    @transaction.atomic
    def queue_all_paper_reassembly(self):
        # first work out which papers are ready
        for pn, data in self.alt_get_all_paper_status().items():
            # check if both id'd and marked
            if not data["identified"] or not data["marked"]:
                continue
            # check if already queued or complete
            if data["reassembled_status"] == "Queued":
                continue
            if data["reassembled_status"] == "Complete" and not data["outdated"]:
                # is complete and not outdated
                continue
            # otherwise build it!
            task = ReassembleTask.objects.get(paper__paper_number=pn)
            print("Queuing up task for ", pn)
            pdf_build = huey_reassemble_paper(pn)
            task.huey_id = pdf_build.id
            task.status = ReassembleTask.QUEUED
            task.save()

    @transaction.atomic
    def get_completed_pdf_files(self):
        """Get list of paths of pdf-files of completed (built) tests papers."""
        return [
            task.pdf_file
            for task in ReassembleTask.objects.filter(status=ReassembleTask.COMPLETE)
        ]

    def get_zipfly_generator(self, short_name, *, chunksize=1024 * 1024):
        paths = [
            {
                "fs": pdf_file.path,
                "n": pdf_file.name,
            }
            for pdf_file in self.get_completed_pdf_files()
        ]

        zfly = zipfly.ZipFly(paths=paths, chunksize=chunksize)
        return zfly.generator()


@db_task(queue="tasks")
def huey_reassemble_paper(paper_number):
    try:
        paper_obj = Paper.objects.get(paper_number=paper_number)
    except Paper.DoesNotExist:
        raise ValueError("No paper with that number")
    task = paper_obj.reassembletask

    reas = ReassembleService()
    with tempfile.TemporaryDirectory() as tempdir:
        save_path = reas.reassemble_paper(paper_obj, tempdir)
        with save_path.open("rb") as f:
            task.pdf_file = File(f, name=save_path.name)
            task.save()
