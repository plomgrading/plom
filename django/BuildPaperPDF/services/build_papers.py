import pathlib
import zipfile
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

    def create_task(self, index: int, huey_id: id, student_name=None, student_id=None):
        """Create and save a PDF-building task to the database"""
        if student_id:
            paper_path = self.papers_to_print / f"exam_{index:04}_{student_id}.pdf"
        else:
            paper_path = self.papers_to_print / f"exam_{index:04}.pdf"

        task = PDFTask(
            paper_number=index,
            huey_id=huey_id,
            pdf_file_path=str(paper_path),
            status="todo",
            student_name=student_name,
            student_id=student_id,
        )
        task.save()
        return task

    def clear_tasks(self):
        """Clear all of the build paper tasks"""
        PDFTask.objects.all().delete()
        if self.papers_to_print.exists():
            shutil.rmtree(self.papers_to_print)
        self.papers_to_print.mkdir()

    def build_n_papers(self, n, spec, qvmap):
        """Build multiple papers without having to sign in/out each time"""
        for i in range(n):
            self.build_single_paper(i + 1, spec, qvmap[i + 1])

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

    def get_pdf_zipfile(self, filename="pdf_zipfile.zip"):
        """compress + save a zip file of all the completed PDFs"""
        completed = PDFTask.objects.filter(status="complete")
        temp_filename = self.papers_to_print / filename
        with zipfile.ZipFile(temp_filename, "w") as zf:
            for pdf in completed:
                pdf_path = pathlib.Path(pdf.pdf_file_path)
                zf.write(pdf_path, pdf_path.name)

        return temp_filename

    def stage_pdf_jobs(self, n, classdict=None):
        """Create n PDFTasks, and save to the database without sending them to Huey.

        If there are prenamed test-papers, save that info too.
        """
        for i in range(n):
            index = i + 1
            student_name = None
            student_id = None
            if classdict and i < len(classdict):
                student = classdict[i]
                if student["paper_number"] > 0:
                    student_id = student["id"]
                    student_name = student["studentName"]

            pdf_job = self.create_task(
                index, None, student_id=student_id, student_name=student_name
            )

    def send_all_tasks(self, spec, qvmap):
        """Send all marked as todo PDF tasks to huey"""
        todo_tasks = PDFTask.objects.filter(status="todo")
        for task in todo_tasks:
            paper_number = task.paper_number
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
        task = get_object_or_404(PDFTask, paper_number=paper_num)

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

    def cancel_single_task(self, paper_num):
        """Cancel a single queued task from Huey"""
        task = get_object_or_404(PDFTask, paper_number=paper_num)
        queue = get_queue("tasks")
        queue.revoke_by_id(task.huey_id)
        task.status = "todo"
        task.save()

    def retry_all_task(self, spec, qvmap):
        """Retry all tasks that have error status"""
        retry_tasks = PDFTask.objects.filter(status="error")
        for task in retry_tasks:
            paper_number = task.paper_number
            pdf_build = self._build_single_paper(
                paper_number, spec, qvmap[paper_number]
            )
            task.huey_id = pdf_build.id
            task.status = "queued"
            task.save()

    def delete_all_task(self):
        self.cancel_all_task()
        PDFTask.objects.all().delete()
