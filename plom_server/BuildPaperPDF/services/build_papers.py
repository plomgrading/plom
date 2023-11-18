# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2022 Brennen Chiu
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2023 Julian Lapenna
# Copyright (C) 2023 Colin B. Macdonald

import pathlib
import random
from tempfile import TemporaryDirectory
import time
from typing import Any, Dict, List, Optional

import zipfly

from plom.create.mergeAndCodePages import make_PDF

from django.conf import settings
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.db import transaction
from django.core.files import File
from django_huey import db_task
from django_huey import get_queue

# TODO: why "staging"? We should talk to the "real" student service
from Preparation.services import StagingStudentService
from Preparation.services import PQVMappingService
from Papers.services import SpecificationService
from Papers.models import Paper
from Preparation.models import PaperSourcePDF
from Base.models import HueyTaskTracker
from ..models import PDFHueyTask


# The decorated function returns a ``huey.api.Result``
# ``context=True`` so that the task knows its ID etc.
@db_task(queue="tasks", context=True, preserve=True)
def huey_build_single_paper(
    papernum: int,
    spec: dict,
    question_versions: Dict[int, int],
    *,
    student_info: Optional[Dict[str, Any]] = None,
    tracker_pk: int,
    task=None,
    _debug_be_flaky: bool = False,
) -> bool:
    """Build a single paper and prename it.

    It is important to understand that running this function starts an
    async task in queue that will run sometime in the future.

    Args:
        papernum:
        spec:
        question_versions:

    Keyword Args:
        student_info: None for a regular blank paper or a dict with
            keys ``"id"`` and ``"name"`` for "prenaming" a paper.
        tracker_pk: a key into the database for anyone interested in
            our progress.
        task: includes our ID in the Huey process queue.
        _debug_be_flaky: for debugging, all take a while and some
            percentage will fail.

    Returns:
        True, no meaning, just as per the Huey docs: "if you need to
        block or detect whether a task has finished".
    """
    with transaction.atomic():
        HueyTaskTracker.objects.get(pk=tracker_pk).transition_to_running(task.id)

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
            for i in range(10):
                print(f"Huey sleep i={i}/10: {task.id}")
                time.sleep(1)
            roll = random.randint(1, 10)
            if roll % 5 == 0:
                raise ValueError(
                    f"DEBUG: deliberately failing creating papernum={papernum}"
                )

        with transaction.atomic():
            tr = PDFHueyTask.objects.get(pk=tracker_pk)
            if tr.obsolete:
                # if result no longer needed, no need to keep the PDF
                tr.transition_to_complete()
            else:
                with save_path.open("rb") as f:
                    tr.pdf_file = File(f, name=save_path.name)
                    tr.transition_to_complete()
            # TODO: should we interact with other non-Obsolete chores?
            # TODO: e.g., reset all other chores as Obsolete?
            # TODO: or would we like last-finished rather than first-finished?
            # TODO: or maybe it should be an error to finish when there is
            # TODO: COMPLETE chore: that is, caller is responsible...

    return True


class BuildPapersService:
    """Generate and stamp test-paper PDFs."""

    base_dir = settings.MEDIA_ROOT
    papers_to_print = base_dir / "papersToPrint"

    @transaction.atomic
    def get_n_complete_tasks(self) -> None:
        """Get the number of PDFHueyTasks that have completed."""
        return PDFHueyTask.objects.filter(status=PDFHueyTask.COMPLETE).count()

    @transaction.atomic
    def get_n_pending_tasks(self) -> None:
        """Get the number of PDFHueyTasks with the status other than 'COMPLETE'.

        This includes ones that are 'TO_DO' and in-progress.
        """
        return PDFHueyTask.objects.exclude(status=PDFHueyTask.COMPLETE).count()

    @transaction.atomic
    def get_n_tasks_started_but_not_complete(self) -> int:
        """Get the number of PDFHueyTasks with the status 'STARTING', 'QUEUED' or 'RUNNING'.

        These are the tasks that users could think of as "in-progress" in situations
        where its not important exactly where they are in the progress.
        """
        return PDFHueyTask.objects.filter(
            Q(status=PDFHueyTask.STARTING)
            | Q(status=PDFHueyTask.QUEUED)
            | Q(status=PDFHueyTask.RUNNING)
        ).count()

    @transaction.atomic
    def get_n_tasks(self) -> int:
        """Get the total number of PDFHueyTasks."""
        return PDFHueyTask.objects.all().count()

    @transaction.atomic
    def are_all_papers_built(self) -> bool:
        """Return True if all of the test-papers have been successfully built."""
        total_tasks = self.get_n_tasks()
        complete_tasks = self.get_n_complete_tasks()
        return total_tasks > 0 and total_tasks == complete_tasks

    @transaction.atomic
    def are_there_errors(self) -> bool:
        """Return True if there are any PDFHueyTasks with an 'error' status."""
        return PDFHueyTask.objects.filter(status=PDFHueyTask.ERROR).count() > 0

    def get_completed_pdf_paths(self) -> list:
        """Get list of paths of pdf-files of completed (built) tests papers."""
        return [
            pdf.file_path()
            for pdf in PDFHueyTask.objects.filter(status=PDFHueyTask.COMPLETE)
        ]

    def stage_all_pdf_jobs(self, classdict=None) -> None:
        """Create all the PDFHueyTasks, and save to the database without sending them to Huey.

        If there are prenamed test-papers, save that info too.
        """
        # TODO: still has callers, be a no-op
        return

    def send_all_tasks(self) -> int:
        """For each Paper without an QUEUED or COMPLETE task, send PDF tasks to huey.

        TODO: but for now, just build them all, independent of what has been done before.
        TODO: that means it can error on our existing non-obsolete: to be considered...

        Returns:
            How many tasks did we launch?
        """
        N = 0
        for paper in Paper.objects.all():
            print(paper)
            # TODO: andrew will make this all pre-fetchy later
            # any_existing_tasks = PDFHueyTask.objects.filter(paper=paper).filter(
            #     Q(status=PDFHueyTask.COMPLETE) | Q(status=PDFHueyTask.QUEUED | Q(status=PDFHueyTask.RUNNING)).exists()
            # if not any_existing_tasks:
            paper_num = paper.paper_number
            self.send_single_task(paper_num)
            N += 1
        return N

    def send_single_task(self, paper_num) -> None:
        """Create a new chore and enqueue a task to Huey to build the PDF for a paper.

        Args:
            paper_num: which paper number

        Raises:
            ObjectDoesNotExist: non-existent paper number.
            ValueError: existing non-obsolete PDFHueyTask for that
                paper number.
        """
        spec = SpecificationService.get_the_spec()

        # TODO: helper looks it up again, just here for error handling :(
        _ = Paper.objects.get(paper_number=paper_num)

        pqv_service = PQVMappingService()
        qvmap = pqv_service.get_pqv_map_dict()
        qv_row = qvmap[paper_num]

        prenamed = StagingStudentService().get_prenamed_papers()
        student_id, student_name = None, None
        if paper_num in prenamed:
            student_id, student_name = prenamed[paper_num]

        self._send_single_task(paper_num, spec, student_name, student_id, qv_row)

    def _send_single_task(
        self,
        paper_num: int,
        spec: dict,
        student_name: Optional[str],
        student_id: Optional[str],
        qv_row: Dict[int, int],
    ) -> None:
        # TODO: error handling!
        paper = Paper.objects.get(paper_number=paper_num)

        # TODO: does the chore really need to know the name and id?  Maybe Huey should put it there...
        with transaction.atomic(durable=True):
            if PDFHueyTask.objects.filter(paper=paper, obsolete=False).exists():
                raise ValueError(
                    f"There are non-obsolete PDFHueyTasks for papernum {paper_num}:"
                    " make them obsolete before creating another"
                )
            task = PDFHueyTask.objects.create(
                paper=paper,
                huey_id=None,
                status=PDFHueyTask.STARTING,
                student_name=student_name,
                student_id=student_id,
            )
            task.save()
            tracker_pk = task.pk

        student_info = None
        if student_name and student_id:
            student_info = {"id": student_id, "name": student_name}
        res = huey_build_single_paper(
            paper_num,
            spec,
            qv_row,
            student_info=student_info,
            tracker_pk=tracker_pk,
            _debug_be_flaky=False,
        )
        print(f"Just enqueued Huey reassembly task id={res.id}")
        with transaction.atomic(durable=True):
            tr = HueyTaskTracker.objects.get(pk=tracker_pk)
            tr.transition_to_queued_or_running(res.id)

    def try_to_cancel_all_queued_tasks(self) -> int:
        """Try to cancel all the queued tasks in the Huey queue.

        If a task is already running, it is probably difficult to cancel
        but we can try to cancel all of the ones that are enqueued.

        This is a "best effort" function, not a promise that will stop
        running tasks.

        It would be embarrassing if something *became* QUEUED after this...
        So we hold atomic DB so no Trackers can transition from STARTING
        to QUEUED state, although I don't think there is a guarantee.

        Returns:
            The number of tasks we tried to revoke.
        """
        N = 0
        queue = get_queue("tasks")
        with transaction.atomic(durable=True):
            queue_tasks = PDFHueyTask.objects.filter(
                Q(status=PDFHueyTask.STARTING) | Q(status=PDFHueyTask.QUEUED)
            )
            for task in queue_tasks:
                task.set_obsolete()
                if task.huey_id:
                    queue.revoke_by_id(str(task.huey_id))
                N += 1
        return N

    def try_to_cancel_single_queued_task(self, paper_number: int):
        """Try to cancel a single queued task from Huey.

        This is a "best effort" function, not a promise that will stop
        running tasks.

        If a task is already running, it is probably difficult to cancel
        but we can try to cancel if starting or enqueued.  Should be harmless
        to call on tasks that have errored out, or are incomplete or are still
        to do.

        TODO: what if it is Complete?  What then?  I'm not sure it should reset
        but currently it does.
        """
        task = get_object_or_404(Paper, paper_number=paper_number).pdfhueytask
        task.set_obsolete()
        if task.huey_id:
            queue = get_queue("tasks")
            queue.revoke_by_id(str(task.huey_id))

    def retry_all_task(self) -> None:
        """Retry all non-obsolete tasks that have error status."""
        retry_tasks = PDFHueyTask.objects.filter(
            status=PDFHueyTask.ERROR, obsolete=False
        )
        for task in retry_tasks:
            paper_number = task.paper.paper_number
            self.send_single_task(paper_number)

    def reset_all_tasks(self) -> None:
        """Reset all tasks, discarding all in-progress and complete PDF files."""
        self.try_to_cancel_all_queued_tasks()
        for task in PDFHueyTask.objects.all():
            task.set_obsolete()

    @transaction.atomic
    def get_all_task_status(self) -> Dict:
        """Get the status of every task and return as a dict."""
        stat = {}
        for task in PDFHueyTask.objects.all():
            stat[task.paper.paper_number] = task.get_status_display()
        return stat

    @transaction.atomic
    def get_paper_path_and_bytes(self, paper_number: int):
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
    def get_task_context(self) -> List[Dict[str, Any]]:
        """Get information about all tasks."""
        return [
            {
                "paper_number": task.paper.paper_number,
                "status": task.get_status_display(),
                "message": task.message,
                "pdf_filename": task.file_display_name(),
                "tmp_pk": task.pk,
                "tmp_huey_id": task.huey_id,
                "tmp_obsolete": task.obsolete,
            }
            # TODO: a loop over papers instead?
            for task in PDFHueyTask.objects.all()
            .select_related("paper")
            .order_by("paper__paper_number")
        ]

    def get_zipfly_generator(self, short_name: str, *, chunksize: int = 1024 * 1024):
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
