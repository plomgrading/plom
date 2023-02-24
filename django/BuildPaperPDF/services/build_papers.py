# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2022 Brennen Chiu
# Copyright (C) 2023 Andrew Rechnitzer

import pathlib
import shutil
import random

from plom.create.mergeAndCodePages import make_PDF

from django.conf import settings
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.db import transaction
from django_huey import db_task
from django_huey import db_task, get_queue

from BuildPaperPDF.models import PDFTask
from Papers.models import Paper


class BuildPapersService:
    """Generate and stamp test-paper PDFs."""

    base_dir = settings.BASE_DIR
    papers_to_print = base_dir / "papersToPrint"

    @transaction.atomic
    def get_n_complete_tasks(self):
        """Get the number of PDFTasks that have completed"""
        completed = PDFTask.objects.filter(status="complete")
        return len(completed)

    @transaction.atomic
    def get_n_pending_tasks(self):
        """Get the number of PDFTasks with the status 'todo,' 'queued,' 'started,' or 'error'"""
        pending = PDFTask.objects.exclude(status="complete")
        return len(pending)

    @transaction.atomic
    def get_n_running_tasks(self):
        """Get the number of PDFTasks with the status 'queued' or 'started"""
        running = PDFTask.objects.filter(Q(status="queued") | Q(status="started"))
        return len(running)

    @transaction.atomic
    def get_n_tasks(self):
        """Get the total number of PDFTasks"""
        return len(PDFTask.objects.all())

    @transaction.atomic
    def are_all_papers_built(self):
        """Return True if all of the test-papers have been successfully built"""
        total_tasks = self.get_n_tasks()
        complete_tasks = self.get_n_complete_tasks()
        return total_tasks > 0 and total_tasks == complete_tasks

    @transaction.atomic
    def are_there_errors(self):
        """Return True if there are any PDFTasks with an 'error' status"""
        error_tasks = PDFTask.objects.filter(status="error")
        return len(error_tasks) > 0

    def create_task(self, index: int, huey_id: id, student_name=None, student_id=None):
        """Create and save a PDF-building task to the database"""
        if student_id:
            paper_path = self.papers_to_print / f"exam_{index:04}_{student_id}.pdf"
        else:
            paper_path = self.papers_to_print / f"exam_{index:04}.pdf"

        paper = get_object_or_404(Paper, paper_number=index)

        task = PDFTask(
            paper=paper,
            huey_id=huey_id,
            pdf_file_path=str(paper_path),
            status="todo",
            student_name=student_name,
            student_id=student_id,
        )
        task.save()
        return task

    @transaction.atomic()
    def clear_tasks(self):
        """Clear all of the build paper tasks"""
        # TODO - improve file handling here when we fix up file handling for all pdf build tasks.
        PDFTask.objects.all().delete()
        if self.papers_to_print.exists():
            shutil.rmtree(self.papers_to_print)
        self.papers_to_print.mkdir(exist_ok=True)

    def build_single_paper(self, index: int, spec: dict, question_versions: dict):
        """Build a single test-paper (with huey!)"""
        pdf_build = self._build_single_paper(index, spec, question_versions)
        task_obj = self.create_task(index, pdf_build.id)
        task_obj.status = "queued"
        task_obj.save()
        return task_obj

    @db_task(queue="tasks")
    def _build_single_paper(index: int, spec: dict, question_versions: dict):
        """Build a single test-paper"""
        make_PDF(spec=spec, papernum=index, question_versions=question_versions)

    @db_task(queue="tasks")
    def _build_prenamed_paper(
        index: int, spec: dict, question_versions: dict, student_info: dict
    ):
        """Build a single test-paper and prename it"""
        make_PDF(
            spec=spec,
            papernum=index,
            question_versions=question_versions,
            extra=student_info,
        )

    @db_task(queue="tasks")
    def _build_flaky_single_paper(index: int, spec: dict, question_versions: dict):
        """DEBUG ONLY: build a test-paper with a random chance of throwing an error"""
        roll = random.randint(1, 10)
        if roll % 5 == 0:
            raise ValueError("Error! This didn't work.")

        make_PDF(spec=spec, papernum=index, question_versions=question_versions)

    def get_completed_pdf_paths(self):
        """Get list of paths of pdf-files of completed (built) tests papers"""
        return [
            pathlib.Path(pdf.pdf_file_path)
            for pdf in PDFTask.objects.filter(status="complete")
        ]

    def stage_all_pdf_jobs(self, classdict=None):
        """Create all the PDFTasks, and save to the database without sending them to Huey.

        If there are prenamed test-papers, save that info too.
        """
        # note - classdict is a list of dicts - change this to more useful format
        prenamed = {X["paper_number"]: X for X in classdict if X["paper_number"] > 0}

        print(classdict)
        self.papers_to_print.mkdir(exist_ok=True)
        for paper_obj in Paper.objects.all():
            paper_number = paper_obj.paper_number
            student_name = None
            student_id = None
            if paper_number in prenamed:
                student_id = prenamed[paper_number]["id"]
                student_name = prenamed[paper_number]["studentName"]

            pdf_job = self.create_task(
                paper_number, None, student_id=student_id, student_name=student_name
            )

    def send_all_tasks(self, spec, qvmap):
        """Send all marked as todo PDF tasks to huey"""
        todo_tasks = PDFTask.objects.filter(status="todo")
        for task in todo_tasks:
            paper_number = task.paper.paper_number
            if task.student_name and task.student_id:
                info_dict = {"id": task.student_id, "name": task.student_name}
                pdf_build = self._build_prenamed_paper(
                    paper_number, spec, qvmap[paper_number], info_dict
                )
            else:
                pdf_build = self._build_single_paper(
                    paper_number, spec, qvmap[paper_number]
                )

            task.huey_id = pdf_build.id
            task.status = "queued"
            task.save()

    def send_single_task(self, paper_num, spec, qv_row):
        """Send a single todo task to Huey"""
        paper = get_object_or_404(Paper, paper_number=paper_num)
        task = paper.pdftask

        if task.student_name and task.student_id:
            info_dict = {"id": task.student_id, "name": task.student_name}
            pdf_build = self._build_prenamed_paper(paper_num, spec, qv_row, info_dict)
        else:
            pdf_build = self._build_single_paper(paper_num, spec, qv_row)

        task.huey_id = pdf_build.id
        task.status = "queued"
        task.save()

    def cancel_all_task(self):
        """Cancel all queued task from Huey"""
        queue_tasks = PDFTask.objects.filter(status="queued")
        for task in queue_tasks:
            queue = get_queue("tasks")
            queue.revoke_by_id(task.huey_id)
            task.status = "todo"
            task.save()

    def cancel_single_task(self, paper_number):
        """Cancel a single queued task from Huey"""
        task = get_object_or_404(Paper, paper_number=paper_number).pdftask
        queue = get_queue("tasks")
        queue.revoke_by_id(task.huey_id)
        task.status = "todo"
        task.save()

    def retry_all_task(self, spec, qvmap):
        """Retry all tasks that have error status"""
        retry_tasks = PDFTask.objects.filter(status="error")
        for task in retry_tasks:
            paper_number = task.paper.paper_number
            pdf_build = self._build_single_paper(
                paper_number, spec, qvmap[paper_number]
            )
            task.huey_id = pdf_build.id
            task.status = "queued"
            task.save()

    @transaction.atomic
    def reset_all_tasks(self):
        self.cancel_all_task()
        for task in PDFTask.objects.all():
            pathlib.Path(task.pdf_file_path).unlink(missing_ok=True)
            task.huey_id = None
            task.status = "todo"
            task.save()

    @transaction.atomic
    def get_all_task_status(self):
        """Get the status of every task and return as a dict"""
        stat = {}
        for task in PDFTask.objects.all():
            stat[task.paper.paper_number] = task.status
        return stat

    @transaction.atomic
    def get_paper_path_and_bytes(self, paper_number):
        """Get the bytes of the file generated by the given task"""
        try:
            task = Paper.objects.get(paper_number=paper_number).pdftask
        except (Paper.DoesNotExist, PDFTask.DoesNotExist):
            raise ValueError(f"Cannot find task {paper_number}")
        if task.status != "complete":
            raise ValueError(f"Task {paper_number} is not complete")

        paper_path = pathlib.Path(task.pdf_file_path)
        with paper_path.open("rb") as fh:
            return (paper_path.name, fh.read())

    @transaction.atomic
    def get_task_context(self):
        """Get information about all tasks"""
        return [
            {
                "paper_number": task.paper.paper_number,
                "status": task.status,
                "message": task.message,
                "pdf_filename": pathlib.Path(task.pdf_file_path).name,
            }
            for task in PDFTask.objects.all()
        ]
