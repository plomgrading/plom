# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Julian Lapenna
# Copyright (C) 2023 Andrew Rechnitzer

from typing import Any, Dict, Union, List, Optional, Tuple

from django.db import transaction
from django.db.models import Count, Min, Max

from Identify.models import PaperIDTask
from Mark.models import MarkingTask
from Papers.models import IDPage, Image, Paper
from Papers.services import SpecificationService


class ProgressOverviewService:
    @transaction.atomic
    def get_id_task_status(self) -> List[Dict]:
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
    def get_marking_task_status(self) -> List[Dict]:
        marking_info = []
        for task in MarkingTask.objects.exclude(
            status=MarkingTask.OUT_OF_DATE
        ).prefetch_related("paper", "latest_annotation", "assigned_user"):
            dat = {
                "paper": task.paper.paper_number,
                "status": task.get_status_display(),
                "question": task.question_number,
                "version": task.question_version,
            }
            if task.status in [MarkingTask.OUT, MarkingTask.COMPLETE]:
                dat["user"] = task.assigned_user.username
            if task.status == MarkingTask.COMPLETE:
                dat["score"] = task.latest_annotation.score
                dat["annotation_pk"] = task.latest_annotation.pk

            marking_info.append(dat)
        return marking_info

    @transaction.atomic
    def get_task_overview(self) -> tuple[Dict, Dict]:
        """Return (id-info, marking-info) dicts with info for all id and marking tasks of every paper in use.

        Note that a paper is in use if it has at least one ID or marking task.

        ID-info dict is either {paper_number: None} if task not present, or {paper_number: data} where data is itself a dict of the form
          * {status: 'To do'} or
          * {'status': 'Out', 'user': username} - the name of the user who has the task
          * {status: 'Complete', 'user': username, 'sid': student_id} - user who did the id'ing and the student-id of that paper.

        Marking-info dict is of the form {paper_number: {1: dat, 2:dat, ..., n: dat} } with data for each question. For each question we have
          * {status: 'To do'} or
          * {'status': 'Out', 'user': username} - the name of the user who has the task
          * {status: 'Complete', 'user': username, 'score': score, 'annotation_pk: blah} - user who did the marking'ing, the score, and the pk of the corresponding annotaiton.
        """
        id_task_overview: Dict[int, Optional[Dict[str, Any]]] = {}
        marking_task_overview: Dict[int, Dict[int, Optional[Dict[str, Any]]]] = {}
        question_numbers = [
            q + 1 for q in range(SpecificationService.get_n_questions())
        ]

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
            marking_task_overview[paper_number] = {qn: None for qn in question_numbers}
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
    def get_completed_marking_task_counts(self) -> Dict:
        """Return dict of number of completed marking tasks for each question."""
        return {
            qi: MarkingTask.objects.filter(
                question_number=qi, status=PaperIDTask.COMPLETE
            ).count()
            for qi in range(1, SpecificationService.get_n_questions() + 1)
        }

    def get_completed_task_counts(self) -> Dict:
        return {
            "id": self.get_completed_id_task_count(),
            "mk": self.get_completed_marking_task_counts(),
        }

    @transaction.atomic
    def get_id_task_status_counts(
        self, n_papers: Optional[int] = None
    ) -> Dict[str, int]:
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
        self, n_papers: Optional[int] = None
    ) -> Dict[int, Dict[str, int]]:
        """Return a dict of counts of marking tasks by their status for each question.

        Note that, if n_papers is supplied, then the number of missing
        tasks is also computed. Also note that this excludes
        out-of-date tasks.
        """
        # return a dict of dict - one for each question-index.
        # for each index the dict is {status: count} for each of todo, complete, out
        # exclude OUT OF DATE tasks
        dat = {
            qi: {"To Do": 0, "Complete": 0, "Out": 0}
            for qi in range(1, SpecificationService.get_n_questions() + 1)
        }
        for X in (
            MarkingTask.objects.exclude(status=MarkingTask.OUT_OF_DATE)
            .values("status", "question_number")
            .annotate(the_count=Count("status"))
        ):
            dat[X["question_number"]][
                MarkingTask(status=X["status"]).get_status_display()
            ] = X["the_count"]
        if n_papers:
            for qi in range(1, SpecificationService.get_n_questions() + 1):
                present = sum([v for x, v in dat[qi].items()])
                dat[qi].update({"Missing": n_papers - present})
        return dat

    @transaction.atomic
    def get_mark_task_status_counts_by_qv(
        self, question_number: int, version: Optional[int] = None
    ) -> Dict[str, int]:
        """Return a dict of counts of marking tasks by their status for the given question/version.

        Note that, if version is not supplied (or None) then count by
        question only. Also note that this excludes out-of-date tasks.

        """
        dat = {"To Do": 0, "Complete": 0, "Out": 0}
        query = MarkingTask.objects.exclude(status=MarkingTask.OUT_OF_DATE).filter(
            question_number=question_number
        )
        # filter by version if supplied
        if version:
            query = query.filter(question_version=version)

        for X in query.values("status").annotate(the_count=Count("status")):
            dat[MarkingTask(status=X["status"]).get_status_display()] = X["the_count"]

        return dat

    @transaction.atomic
    def get_first_last_used_paper_number(self) -> Tuple[int, int]:
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
