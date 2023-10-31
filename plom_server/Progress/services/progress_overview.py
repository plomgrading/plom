# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Julian Lapenna
# Copyright (C) 2023 Andrew Rechnitzer

from typing import Any, Dict, Union, List, Optional

from django.db import transaction

from Identify.models import PaperIDTask
from Mark.models import MarkingTask
from Papers.models import IDPage, Image
from Papers.services import SpecificationService


class ProgressOverviewService:
    @transaction.atomic
    def get_id_task_status(self) -> List[Dict]:
        id_info = []
        for task in PaperIDTask.objects.exclude(
            status=PaperIDTask.OUT_OF_DATE
        ).prefetch_related("paper", "latest_action"):
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
    def get_completed_task_counts(self) -> Dict:
        task_counts = {
            "id": PaperIDTask.objects.filter(status=PaperIDTask.COMPLETE).count(),
            "mk": {},
        }

        for qn in range(1, SpecificationService.get_n_questions() + 1):
            task_counts["mk"].update(
                {
                    qn: MarkingTask.objects.filter(
                        question_number=qn, status=PaperIDTask.COMPLETE
                    ).count()
                }
            )
        return task_counts
