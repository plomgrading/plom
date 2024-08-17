# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2022 Brennen Chiu
# Copyright (C) 2023-2024 Andrew Rechnitzer
# Copyright (C) 2023 Julian Lapenna
# Copyright (C) 2023-2024 Colin B. Macdonald
# Copyright (C) 2024 Aden Chan

from __future__ import annotations

import pathlib
import random
from tempfile import TemporaryDirectory
import time
from typing import Any

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
from Preparation.services import (
    StagingStudentService,
    PQVMappingService,
    PrenameSettingService,
)
from Papers.services import SpecificationService
from Papers.models import Paper
from Preparation.models import PaperSourcePDF
from Base.models import HueyTaskTracker
from ..models import BuildPaperPDFChore

from Preparation.services.preparation_dependency_service import (
    assert_can_rebuild_test_pdfs,
)


# The decorated function returns a ``huey.api.Result``
# ``context=True`` so that the task knows its ID etc.
@db_task(queue="tasks", context=True)
def huey_build_single_paper(
    papernum: int,
    spec: dict,
    question_versions: dict[int, int],
    *,
    student_info: dict[str, Any] | None = None,
    prename_config: dict[str, Any] | None = None,
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
        prename_config: A dict containing keys ``"xcoord"`` and
            ``"ycoord"``, used to position the prename box on the ID page.
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
    # just pass xcoord and ycoord as kwargs, None is an acceptable input
    with TemporaryDirectory() as tempdir:
        save_path = make_PDF(
            spec=spec,
            papernum=papernum,
            question_versions=question_versions,
            extra=student_info,
            xcoord=prename_config["xcoord"],
            ycoord=prename_config["ycoord"],
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
            _chore = BuildPaperPDFChore.objects.select_for_update().get(pk=tracker_pk)
            if not _chore.obsolete:
                with save_path.open("rb") as f:
                    _chore.pdf_file = File(f, name=save_path.name)
                    _chore.display_filename = save_path.name
                    _chore.save()

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

    def are_any_papers_built(self) -> bool:
        """Return true if any papers have had their PDFs built successfully."""
        return BuildPaperPDFChore.objects.filter(
            status=BuildPaperPDFChore.COMPLETE, obsolete=False
        ).exists()

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

    def get_completed_pdf_files_and_names(self) -> list[tuple[File, str]]:
        """Get list of Files and recommended names of pdf-files of completed (built) tests papers."""
        return [
            (pdf.pdf_file, pdf.display_filename)
            for pdf in BuildPaperPDFChore.objects.filter(
                obsolete=False, status=BuildPaperPDFChore.COMPLETE
            )
        ]

    def send_all_tasks(self) -> int:
        """For each Paper without an QUEUED or COMPLETE chore, start building PDFs.

        Raises:
            PlomDependencyConflict: if dependencies not met.

        Returns:
            How many tasks did we launch?
        """
        assert_can_rebuild_test_pdfs()
        # first we set all tasks with status=error as obsolete.
        BuildPaperPDFChore.set_every_task_with_status_error_obsolete()
        # now iterate over papers that have zero non-obsolete chores.
        papers_to_build = []
        for paper in Paper.objects.all():
            # if the paper has some non-obsolete chore - do not rebuild
            if paper.buildpaperpdfchore_set.filter(obsolete=False).exists():
                pass
            else:  # rebuild this paper's pdf
                papers_to_build.append(paper.paper_number)

        self._send_list_of_tasks(papers_to_build)
        return len(papers_to_build)

    def send_single_task(self, paper_num: int):
        """Start building the PDF for the given paper, provided it does not have a QUEUED or COMPLETE chore.

        Raises:
            PlomDependencyConflict: if dependencies not met.
        """
        self._send_list_of_tasks([paper_num])

    def _send_list_of_tasks(self, paper_number_list: list[int]) -> None:
        """Create a new list of chores and enqueue the tasks to Huey to build PDF for papers.

        If there is a existing chore, it will be set to obsolete.

        Args:
            paper_number_list: which paper number - entries must be unique.

        Raises:
            ObjectDoesNotExist: non-existent paper number.
            PlomDependencyConflict: if dependencies not met
        """
        assert_can_rebuild_test_pdfs()

        # get all the qvmap and student-id/name info
        spec = SpecificationService.get_the_spec()
        pqv_service = PQVMappingService()
        qvmap = pqv_service.get_pqv_map_dict()
        prenamed = StagingStudentService().get_prenamed_papers()
        prename_config = PrenameSettingService().get_prenaming_coords()

        the_papers = Paper.objects.filter(paper_number__in=paper_number_list)
        # Check paper-numbers all legal and store the corresponding paper-objects
        check = the_papers.count()
        if check != len(paper_number_list):
            raise ObjectDoesNotExist(
                "Could not find all papers from supplied list of paper_numbers."
            )

        with transaction.atomic(durable=True):
            # first set any existing non-obsolete chores to obsolete
            for chore in BuildPaperPDFChore.objects.filter(
                obsolete=False, paper__paper_number__in=paper_number_list
            ):
                chore.set_as_obsolete()
            # now make a list of new chores as they are created
            chore_list = []
            # Quick fix but maybe it should be an error for the_papers to be empty?
            paper = None
            for paper in the_papers:
                if paper.paper_number in prenamed:
                    student_id, student_name = prenamed[paper.paper_number]
                else:
                    student_id, student_name = None, None
                chore_list.append(
                    BuildPaperPDFChore.objects.create(
                        paper=paper,
                        huey_id=None,
                        status=BuildPaperPDFChore.STARTING,
                        student_name=student_name,
                        student_id=student_id,
                    )
                )
            del paper

        # for each of the newly created chores, actually ask Huey to run them
        chore_pk_huey_id_list = []
        for chore in chore_list:
            if chore.student_name and chore.student_id:
                student_info = {"id": chore.student_id, "name": chore.student_name}
            else:
                student_info = None
            res = huey_build_single_paper(
                chore.paper.paper_number,
                spec,
                qvmap[chore.paper.paper_number],
                student_info=student_info,
                prename_config=prename_config,
                tracker_pk=chore.pk,
                _debug_be_flaky=False,
            )
            chore_pk_huey_id_list.append((chore.pk, res.id))
        HueyTaskTracker.bulk_transition_to_queued_or_running(chore_pk_huey_id_list)

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
            ).select_for_update()
            for task in queue_tasks:
                if task.huey_id:
                    queue.revoke_by_id(str(task.huey_id))
                task.transition_to_error("never ran: forcibly dequeued")
                N += 1
        return N

    def try_to_cancel_single_queued_task(self, paper_number: int) -> None:
        """Try to cancel a single queued task from Huey.

        This is a "best effort" function, not a promise that will stop
        running tasks.

        If a task is already running, it is probably difficult to cancel
        but we can try to cancel if starting or enqueued.  Should be harmless
        to call on tasks that have errored out, or are incomplete or are still
        to do.

        If the task is Complete, this should have no effect on it.
        """
        task = BuildPaperPDFChore.objects.get(
            obsolete=False, paper__paper_number=paper_number
        )
        if task.huey_id:
            queue = get_queue("tasks")
            queue.revoke_by_id(str(task.huey_id))
        if task.status in (BuildPaperPDFChore.STARTING, BuildPaperPDFChore.QUEUED):
            task.transition_to_error("never ran: forcibly dequeued")

    def retry_all_task(self) -> None:
        """Retry all non-obsolete tasks that have error status.

        Raises:
            PlomDependencyConflict: if dependencies not met.
        """
        assert_can_rebuild_test_pdfs()

        retry_tasks = BuildPaperPDFChore.objects.filter(
            status=BuildPaperPDFChore.ERROR, obsolete=False
        )
        for task in retry_tasks:
            paper_number = task.paper.paper_number
            self.send_single_task(paper_number)

    def reset_all_tasks(self) -> None:
        """Reset all tasks, discarding all in-progress and complete PDF files.

        Raises:
            PlomDependencyConflict: if dependencies not met.
        """
        assert_can_rebuild_test_pdfs()
        self.try_to_cancel_all_queued_tasks()
        with transaction.atomic():
            # bulk set all obsolete and delete associated files
            BuildPaperPDFChore.set_every_task_obsolete(unlink_files=True)

    @transaction.atomic
    def get_all_task_status(self) -> dict[int, str]:
        """Get the status of every task and return as a dict."""
        return {
            task.paper.paper_number: task.get_status_display()
            for task in BuildPaperPDFChore.objects.exclude(obsolete=True)
        }

    @transaction.atomic
    def get_paper_recommended_name_and_bytes(
        self, paper_number: int
    ) -> tuple[str, bytes]:
        """Get the bytes of the file generated by the given task."""
        try:
            task = BuildPaperPDFChore.objects.get(
                obsolete=False, paper__paper_number=paper_number
            )
        except ObjectDoesNotExist as e:
            raise ValueError(f"Cannot find PDF for {paper_number}: {e}")
        if task.status != BuildPaperPDFChore.COMPLETE:
            raise ValueError(f"Task {paper_number} is not complete")

        return (task.display_filename, task.pdf_file.read())

    @transaction.atomic
    def get_task_context(
        self, *, include_obsolete: bool = False
    ) -> list[dict[str, Any]]:
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
                "pdf_filename": task.display_filename,
            }
            for task in tasks
        ]

    def get_zipfly_generator(self, short_name: str, *, chunksize: int = 1024 * 1024):
        """Get a dynamic zip file streamer generator for all the PDF files.

        Raises:
            ValueError: no papers available.
        """
        paths = [
            {
                "fs": pdf_path.path,
                "n": f"papers_for_{short_name}/{display_filename}",
            }
            for pdf_path, display_filename in self.get_completed_pdf_files_and_names()
        ]
        if len(paths) == 0:
            raise ValueError("No PDF files are built")

        zfly = zipfly.ZipFly(paths=paths, chunksize=chunksize)
        return zfly.generator()
