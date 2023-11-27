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
from django.db.models import Q
from django.db import transaction
from django.core.files import File
from django.core.exceptions import ObjectDoesNotExist
from django_huey import db_task
from django_huey import get_queue

# TODO: why "staging"? We should talk to the "real" student service
from Preparation.services import StagingStudentService
from Preparation.services import PQVMappingService
from Papers.services import SpecificationService
from Papers.models import Paper
from Preparation.models import PaperSourcePDF
from Base.models import HueyTaskTracker
from ..models import BuildPaperPDFChore


# The decorated function returns a ``huey.api.Result``
# ``context=True`` so that the task knows its ID etc.
@db_task(queue="tasks", context=True)
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
    The implementation starts with a "transition to running" and ends
    with an "transition to complete": one needs to be a bit careful about
    these to avoid race conditions with the caller.  In the future we
    might consider using a decorator for this pattern instead.

    Args:
        papernum: which paper to assemble
        spec: the specification of the assessment.
        question_versions: which version to use for each question.
            A row of the "qvmap".

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
    HueyTaskTracker.transition_to_running(tracker_pk, task.id)

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
            for i in range(5):
                print(f"Huey sleep i={i}/4: {task.id}")
                time.sleep(1)
            roll = random.randint(1, 10)
            if roll % 5 == 0:
                raise ValueError(
                    f"DEBUG: deliberately failing creating papernum={papernum}"
                )

        with transaction.atomic(durable=True):
            chore = BuildPaperPDFChore.objects.select_for_update().get(pk=tracker_pk)
            if not chore.obsolete:
                with save_path.open("rb") as f:
                    chore.pdf_file = File(f, name=save_path.name)
                    chore.save()

    HueyTaskTracker.transition_to_complete(tracker_pk)
    return True


class BuildPapersService:
    """Generate and stamp test-paper PDFs."""

    base_dir = settings.MEDIA_ROOT
    papers_to_print = base_dir / "papersToPrint"

    def get_n_papers(self) -> int:
        """Get the number of Papers."""
        return Paper.objects.count()

    def get_n_complete_tasks(self) -> int:
        """Get the number of chores that have completed."""
        return BuildPaperPDFChore.objects.filter(
            status=BuildPaperPDFChore.COMPLETE, obsolete=False
        ).count()

    def get_n_obsolete_tasks(self) -> int:
        """Get the number of obsolete chores."""
        return BuildPaperPDFChore.objects.filter(obsolete=True).count()

    @transaction.atomic
    def get_n_tasks_started_but_not_complete(self) -> int:
        """Get the number of chores with the status 'STARTING', 'QUEUED' or 'RUNNING'.

        These are the tasks that users could think of as "in-progress" in situations
        where its not important exactly where they are in the progress.
        """
        return (
            BuildPaperPDFChore.objects.filter(obsolete=False)
            .filter(
                Q(status=BuildPaperPDFChore.STARTING)
                | Q(status=BuildPaperPDFChore.QUEUED)
                | Q(status=BuildPaperPDFChore.RUNNING)
            )
            .count()
        )

    def get_n_tasks(self) -> int:
        """Get the total number of non-obsolete chores."""
        return BuildPaperPDFChore.objects.filter(obsolete=False).count()

    @transaction.atomic
    def are_all_papers_built(self) -> bool:
        """Return True if all of the papers have had their PDF built successfully.

        If there are no Papers, we still return False (despite this being technically
        trivially true).
        """
        num_papers = self.get_n_papers()
        if not num_papers:
            # special case for no papers exist
            return False
        # instead of checking that each paper has one, just compare numbers
        return num_papers == self.get_n_complete_tasks()

    @transaction.atomic
    def are_there_errors(self) -> bool:
        """Return True if there are any chores with an 'error' status."""
        return BuildPaperPDFChore.objects.filter(
            obsolete=False, status=BuildPaperPDFChore.ERROR
        ).exists()

    def get_completed_pdf_paths(self) -> list:
        """Get list of paths of pdf-files of completed (built) tests papers."""
        return [
            pdf.file_path()
            for pdf in BuildPaperPDFChore.objects.filter(
                obsolete=False, status=BuildPaperPDFChore.COMPLETE
            )
        ]

    def send_all_tasks(self) -> int:
        """For each Paper without an QUEUED or COMPLETE chore, start building PDFs.

        Returns:
            How many tasks did we launch?
        """
        N = 0
        for paper in Paper.objects.all():
            # This logic and flow is unpleasant...
            # TODO: andrew may want to help make this all pre-fetchy later
            # There are two things we need to build:
            #   - Papers with no chore (non-obsolete)
            #   - Papers with a Error chore (non-obsolete)
            _do_build = False
            try:
                existing_task = BuildPaperPDFChore.objects.get(
                    paper=paper, obsolete=False
                )
            except ObjectDoesNotExist:
                _do_build = True
            else:
                if existing_task.status == BuildPaperPDFChore.ERROR:
                    _do_build = True
                    existing_task.set_as_obsolete()
            if _do_build:
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
            ValueError: existing non-obsolete chores for that paper number.
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
            if BuildPaperPDFChore.objects.filter(paper=paper, obsolete=False).exists():
                raise ValueError(
                    f"There are non-obsolete BuildPaperPDFChores for papernum {paper_num}:"
                    " make them obsolete before creating another"
                )
            task = BuildPaperPDFChore.objects.create(
                paper=paper,
                huey_id=None,
                status=BuildPaperPDFChore.STARTING,
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
        HueyTaskTracker.transition_to_queued_or_running(tracker_pk, res.id)

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
            queue_tasks = BuildPaperPDFChore.objects.filter(
                Q(status=BuildPaperPDFChore.STARTING)
                | Q(status=BuildPaperPDFChore.QUEUED)
            )
            for task in queue_tasks:
                if task.huey_id:
                    queue.revoke_by_id(str(task.huey_id))
                task.set_as_obsolete_with_error("never ran: forcibly dequeued")
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
        task = BuildPaperPDFChore.objects.get(
            obsolete=False, paper__paper_number=paper_number
        )
        task.set_as_obsolete()
        if task.huey_id:
            queue = get_queue("tasks")
            queue.revoke_by_id(str(task.huey_id))
        if task.status in (BuildPaperPDFChore.STARTING, BuildPaperPDFChore.QUEUED):
            task.set_as_obsolete_with_error("never ran: forcibly dequeued")

    def retry_all_task(self) -> None:
        """Retry all non-obsolete tasks that have error status."""
        retry_tasks = BuildPaperPDFChore.objects.filter(
            status=BuildPaperPDFChore.ERROR, obsolete=False
        )
        for task in retry_tasks:
            paper_number = task.paper.paper_number
            self.send_single_task(paper_number)

    def reset_all_tasks(self) -> None:
        """Reset all tasks, discarding all in-progress and complete PDF files."""
        self.try_to_cancel_all_queued_tasks()
        for task in BuildPaperPDFChore.objects.all():
            task.set_as_obsolete()

    @transaction.atomic
    def get_all_task_status(self) -> Dict[int, str]:
        """Get the status of every task and return as a dict."""
        return {
            task.paper.paper_number: task.get_status_display()
            for task in BuildPaperPDFChore.objects.exclude(obsolete=True)
        }

    @transaction.atomic
    def get_paper_path_and_bytes(self, paper_number: int):
        """Get the bytes of the file generated by the given task."""
        try:
            task = BuildPaperPDFChore.objects.get(
                obsolete=False, paper__paper_number=paper_number
            )
        except ObjectDoesNotExist as e:
            raise ValueError(f"Cannot find PDF for {paper_number}: {e}")
        if task.status != BuildPaperPDFChore.COMPLETE:
            raise ValueError(f"Task {paper_number} is not complete")

        paper_path = task.file_path()
        with paper_path.open("rb") as fh:
            return (paper_path.name, fh.read())

    @transaction.atomic
    def get_task_context(self, include_obsolete: bool = False) -> List[Dict[str, Any]]:
        """Get information about all tasks.

        Keyword Args:
            include_obsolete: include any obsolete chores.
        """
        tasks = BuildPaperPDFChore.objects
        if not include_obsolete:
            tasks = tasks.filter(obsolete=False)
        tasks = tasks.select_related("paper").order_by("paper__paper_number")
        return [
            {
                "paper_number": task.paper.paper_number,
                "obsolete": task.obsolete,
                "status": task.get_status_display(),
                "message": task.message,
                "pdf_filename": task.file_display_name(),
            }
            for task in tasks
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
