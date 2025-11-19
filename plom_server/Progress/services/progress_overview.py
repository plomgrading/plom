# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Julian Lapenna
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2024-2025 Colin B. Macdonald

from typing import Any

from django.db import transaction
from django.db.models import Count, Min, Max

from plom.misc_utils import pprint_score

from plom_server.Identify.models import PaperIDTask
from plom_server.Mark.models import MarkingTask
from plom_server.Papers.services import SpecificationService


class ProgressOverviewService:
    @transaction.atomic
    def get_id_task_status(self) -> list[dict]:
        id_info = []
        for task in PaperIDTask.objects.exclude(
            status=PaperIDTask.OUT_OF_DATE
        ).prefetch_related("paper", "latest_action", "assigned_user"):
            dat = {
                "paper": task.paper.paper_number,
                "status": task.get_status_display(),
            }
            if task.status in [PaperIDTask.OUT, PaperIDTask.COMPLETE]:
                dat["user"] = task.assigned_user.username
            if task.status == MarkingTask.COMPLETE:
                dat["sid"] = task.latest_action.student_id
            id_info.append(dat)

        return id_info

    @transaction.atomic
    def get_marking_task_status(self) -> list[dict]:
        marking_info = []
        for task in MarkingTask.objects.exclude(
            status=MarkingTask.OUT_OF_DATE
        ).prefetch_related("paper", "latest_annotation", "assigned_user"):
            # task status is one of to_do, out, complete
            dat = {
                "paper": task.paper.paper_number,
                "status": task.get_status_display(),
                "question": task.question_index,
                "version": task.question_version,
                "task_pk": task.pk,
            }
            if task.status == MarkingTask.OUT:
                dat["user"] = task.assigned_user.username
            if task.status == MarkingTask.COMPLETE:
                dat["user"] = task.assigned_user.username
                dat["score"] = task.latest_annotation.score
                dat["score_str"] = pprint_score(task.latest_annotation.score)

            marking_info.append(dat)
        return marking_info

    @transaction.atomic
    def get_task_overview(self) -> tuple[dict, dict]:
        """Return (id-info, marking-info) dicts with info for all id and marking tasks of every paper in use.

        Note that a paper is in use if it has at least one ID or marking task.

        ID-info dict is either {paper_number: None} if task not present, or {paper_number: data} where data is itself a dict of the form
          * {status: 'To do'} or
          * {'status': 'Out', 'user': username} - the name of the user who has the task
          * {status: 'Complete', 'user': username, 'sid': student_id} - user who did the id'ing and the student-id of that paper.

        Marking-info dict is of the form {paper_number: {1: dat, 2:dat, ..., n: dat} } with data for each question. For each question we have
          * {status: 'To do', 'task_pk': blah} or
          * {'status': 'Out', 'user': username, 'task_pk': blah} - the name of the user who has the task
          * {status: 'Complete', 'user': username, 'score': score, 'task_pk: blah} - user who did the marking'ing, the score, and the pk of the corresponding marking task.
        """
        id_task_overview: dict[int, None | dict[str, Any]] = {}
        marking_task_overview: dict[int, dict[int, None | dict[str, Any]]] = {}
        question_indices = SpecificationService.get_question_indices()

        id_info = self.get_id_task_status()
        marking_info = self.get_marking_task_status()
        # get all the paper numbers that have **some** task
        papers_with_id_task = [X["paper"] for X in id_info]
        papers_with_marking_task = [X["paper"] for X in marking_info]
        papers_with_some_task = list(
            set(papers_with_id_task + papers_with_marking_task)
        )
        # now set up the over-view dicts so that we know about any missing tasks
        for paper_number in papers_with_some_task:
            id_task_overview[paper_number] = None
            marking_task_overview[paper_number] = {qn: None for qn in question_indices}
        # now put the data into those dictionaries
        # we will have Nones where the tasks are missing
        for dat in id_info:
            id_task_overview[dat["paper"]] = dat
        for dat in marking_info:
            marking_task_overview[dat["paper"]][dat["question"]] = dat

        return (id_task_overview, marking_task_overview)

    @transaction.atomic
    def get_completed_id_task_count(self) -> int:
        """Return number of completed ID tasks."""
        return PaperIDTask.objects.filter(status=PaperIDTask.COMPLETE).count()

    @transaction.atomic
    def get_completed_marking_task_counts(self) -> dict:
        """Return dict of number of completed marking tasks for each question."""
        return {
            qi: MarkingTask.objects.filter(
                question_index=qi, status=PaperIDTask.COMPLETE
            ).count()
            for qi in SpecificationService.get_question_indices()
        }

    def get_completed_task_counts(self) -> dict:
        return {
            "id": self.get_completed_id_task_count(),
            "mk": self.get_completed_marking_task_counts(),
        }

    @transaction.atomic
    def get_id_task_status_counts(self, n_papers: int | None = None) -> dict[str, int]:
        """Return a dict of counts of ID tasks by their status.

        Note that this excludes out-of-date tasks.
        """
        dat = {"To Do": 0, "Complete": 0, "Out": 0}
        dat.update(
            {
                PaperIDTask(status=X["status"]).get_status_display(): X["the_count"]
                for X in PaperIDTask.objects.exclude(status=PaperIDTask.OUT_OF_DATE)
                .values("status")
                .annotate(the_count=Count("status"))
            }
        )
        # if n_papers is included then compute how many tasks as "missing"
        if n_papers:
            present = sum([v for x, v in dat.items()])
            dat.update({"Missing": n_papers - present})
        return dat

    @transaction.atomic
    def get_mark_task_status_counts(
        self, n_papers: int | None = None
    ) -> dict[int, dict[str, int]]:
        """Return a dict of counts of marking tasks by their status for each question.

        Keyword Args:
            n_papers: if is supplied, then the number of missing
                tasks is also computed. Also note that this excludes
                out-of-date tasks.

        Returns:
            A dict of dict - one for each question-index.
            For each index the dict is "{status: count}" for each of
            "To Do", "Complete", "Out".  If `n_papers`` was specified
            there is also "Missing".
        """
        qindices = SpecificationService.get_question_indices()
        dat = {qi: {"To Do": 0, "Complete": 0, "Out": 0} for qi in qindices}
        for X in (
            MarkingTask.objects.exclude(status=MarkingTask.OUT_OF_DATE)
            .values("status", "question_index")
            .annotate(the_count=Count("status"))
        ):
            dat[X["question_index"]][
                MarkingTask(status=X["status"]).get_status_display()
            ] = X["the_count"]
        if n_papers is not None:
            for qi, d in dat.items():
                present = sum([v for x, v in d.items()])
                d.update({"Missing": n_papers - present})
        return dat

    @transaction.atomic
    def get_mark_task_status_counts_by_qv(
        self, question_index: int, version: int | None = None
    ) -> dict[str, int]:
        """Return a dict of counts of marking tasks by their status for the given question/version.

        Note that, if version is not supplied (or None) then count by
        question only. Also note that this excludes out-of-date tasks.

        """
        dat = {"To Do": 0, "Complete": 0, "Out": 0}
        query = MarkingTask.objects.exclude(status=MarkingTask.OUT_OF_DATE).filter(
            question_index=question_index
        )
        # filter by version if supplied
        if version:
            query = query.filter(question_version=version)

        for X in query.values("status").annotate(the_count=Count("status")):
            dat[MarkingTask(status=X["status"]).get_status_display()] = X["the_count"]

        return dat

    @transaction.atomic
    def get_first_last_used_paper_number(self) -> tuple[int, int]:
        """Return the first/last paper that has some marking or iding task."""
        # include a default of 1 in case there are no valid id or marking tasks
        min_max_from_marking = MarkingTask.objects.exclude(
            status=MarkingTask.OUT_OF_DATE
        ).aggregate(
            Min("paper__paper_number", default=1), Max("paper__paper_number", default=1)
        )

        min_max_from_iding = PaperIDTask.objects.exclude(
            status=MarkingTask.OUT_OF_DATE
        ).aggregate(
            Min("paper__paper_number", default=1), Max("paper__paper_number", default=1)
        )

        pn_min = min(
            min_max_from_marking["paper__paper_number__min"],
            min_max_from_iding["paper__paper_number__min"],
        )
        pn_max = max(
            min_max_from_marking["paper__paper_number__max"],
            min_max_from_iding["paper__paper_number__max"],
        )

        return (pn_min, pn_max)
