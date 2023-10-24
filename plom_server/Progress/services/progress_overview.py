# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Julian Lapenna
# Copyright (C) 2023 Andrew Rechnitzer

from typing import Dict, Union, List

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
    def get_task_overview(self) -> Dict:
        task_overview = {}
        question_numbers = [
            q + 1 for q in range(SpecificationService.get_n_questions())
        ]
        id_info = self.get_id_task_status()
        marking_info = self.get_marking_task_status()
        # set up the dict carefully for papers with potentially missing tasks
        for X in id_info:
            task_overview[X["paper"]] = {
                "id": None,
                "mk": {qn: None for qn in question_numbers},
            }
        for X in marking_info:
            task_overview[X["paper"]] = {
                "id": None,
                "mk": {qn: None for qn in question_numbers},
            }
        # now put data into that dict
        for dat in id_info:
            task_overview[dat["paper"]]["id"] = dat
        for dat in marking_info:
            task_overview[dat["paper"]]["mk"][dat["question"]] = dat

        return task_overview

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
