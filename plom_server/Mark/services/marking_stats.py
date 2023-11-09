# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Andrew Rechnitzer

import arrow
import statistics
from typing import Any, Dict, List, Optional
from django.db import transaction

from Papers.services import SpecificationService
from Papers.models import Paper
from ..models import MarkingTask, AnnotationImage


class MarkingStatsService:
    """Functions for getting marking stats."""

    @transaction.atomic
    def get_basic_marking_stats(
        self, question: int, *, version: Optional[int] = None
    ) -> Dict[str, Any]:
        """Send back current marking statistics for the given question + version.

        Args:
            question: the question to compute for

        Keyword Args:
            version: optionally, a specific version, or get for all versions if omitted.

        Returns:
            Dictionary containing the following, 'number_of_completed_tasks',
                'all_task_count', 'completed_percentage', 'mark_max', 'mark_min',
                'mark_median', 'mark_mean', 'mark_mode', 'mark_stdev', 'mark_full'
        """
        stats_dict = {
            "number_of_completed_tasks": 0,
            "all_task_count": 0,
            "completed_percentage": 0,
            "mark_max": 0,
            "mark_min": 0,
            "mark_median": 0,
            "mode_mean": 0,
            "mode_mode": 0,
            "mark_stdev": "n/a",
            "avg_marking_time": 0,
            "mark_full": SpecificationService.get_question_mark(question),
        }

        try:
            all_tasks = MarkingTask.objects.filter(question_number=question).exclude(
                status=MarkingTask.OUT_OF_DATE
            )
            completed_tasks = MarkingTask.objects.filter(
                status=MarkingTask.COMPLETE,
                question_number=question,
            ).prefetch_related("latest_annotation")
            if version:
                all_tasks = all_tasks.filter(question_version=version)
                completed_tasks = completed_tasks.filter(question_version=version)

        except MarkingTask.DoesNotExist:
            return stats_dict

        all_task_count = all_tasks.count()
        if all_task_count == 0:
            return stats_dict

        stats_dict["number_of_completed_tasks"] = completed_tasks.count()
        stats_dict["all_task_count"] = all_task_count
        stats_dict["remaining_task_count"] = (
            stats_dict["all_task_count"] - stats_dict["number_of_completed_tasks"]
        )
        stats_dict["completed_percentage"] = round(
            stats_dict["number_of_completed_tasks"] / stats_dict["all_task_count"] * 100
        )

        if stats_dict["number_of_completed_tasks"]:
            stats_dict["avg_marking_time"] = round(
                sum([X.latest_annotation.marking_time for X in completed_tasks])
                / stats_dict["number_of_completed_tasks"]
            )
            stats_dict["approx_remaining_hours"] = round(
                stats_dict["avg_marking_time"]
                * stats_dict["remaining_task_count"]
                / 3600,
                2,
            )
            # the following don't make sense until something is marked
            mark_list = [X.latest_annotation.score for X in completed_tasks]
            stats_dict["mark_max"] = max(mark_list)
            stats_dict["mark_min"] = min(mark_list)
            stats_dict["mark_median"] = round(statistics.median(mark_list), 1)
            stats_dict["mark_mean"] = round(statistics.mean(mark_list), 1)
            stats_dict["mark_mode"] = statistics.mode(mark_list)
            if len(mark_list) >= 2:
                stats_dict["mark_stdev"] = round(statistics.stdev(mark_list), 1)
            else:
                stats_dict["mark_stdev"] = "n/a"

        return stats_dict

    @transaction.atomic
    def get_mark_histogram(
        self, question: int, *, version: Optional[int] = None
    ) -> Dict[int, int]:
        """Get the histogram of marks for the given question, version.

        Args:
            question: the question to compute for

        Keyword Args:
            version: optionally, a specific version, or get for all versions if omitted.


        Returns:
            The histogram as a dict of mark vs count.

        """
        hist = {
            qm: 0 for qm in range(SpecificationService.get_question_mark(question) + 1)
        }
        try:
            completed_tasks = MarkingTask.objects.filter(
                status=MarkingTask.COMPLETE,
                question_number=question,
            ).prefetch_related("latest_annotation")
            if version:
                completed_tasks.filter(question_version=version)
        except MarkingTask.DoesNotExist:
            return hist
        for X in completed_tasks:
            hist[X.latest_annotation.score] += 1
        return hist

    @transaction.atomic
    def get_list_of_users_who_marked(
        self, question: int, *, version: Optional[int] = None
    ) -> List[str]:
        """Return a list of the usernames that marked the given question/version.

        Args:
            question: the question to compute for.

        Keyword Args:
            version: optionally, a specific version, or get for all versions if omitted.

        Returns:
            The usernames of the markers of the given question/version.
        """
        tasks = MarkingTask.objects.filter(
            status=MarkingTask.COMPLETE,
            question_number=question,
        )
        if version:
            tasks = tasks.filter(question_version=version)

        return [
            X.assigned_user.username
            for X in tasks.prefetch_related("assigned_user").distinct("assigned_user")
        ]

    @transaction.atomic
    def get_mark_histogram_and_stats_by_users(
        self, question: int, version: int
    ) -> Dict[int, Dict[str, Any]]:
        """Get marking histogram and stats for the given question/version separated by user.

        Args:
            question (int): The question
            version (int): THe version

        Returns:
            dict (int, dict[str,any]): for each user-pk give a dict that
            contains 'username', 'histogram', 'number', 'mark_max, 'mark_min',
            'mark_median', 'mark_mean', 'mark_mode', 'mark_stdev'.
        """
        data: Dict[int, Dict[str, Any]] = {}
        try:
            completed_tasks = MarkingTask.objects.filter(
                status=MarkingTask.COMPLETE,
                question_number=question,
                question_version=version,
            ).prefetch_related(
                "latest_annotation",
                "assigned_user",
            )
        except MarkingTask.DoesNotExist:
            return data
        for X in completed_tasks:
            if X.assigned_user.pk not in data:
                data[X.assigned_user.pk] = {
                    "username": X.assigned_user.username,
                    "histogram": {
                        qm: 0
                        for qm in range(
                            SpecificationService.get_question_mark(question) + 1
                        )
                    },
                }
            data[X.assigned_user.pk]["histogram"][X.latest_annotation.score] += 1

        for upk in data:
            mark_list = [
                key
                for key, value in data[upk]["histogram"].items()
                for _ in range(value)
            ]
            data[upk]["number"] = len(mark_list)
            data[upk]["mark_max"] = max(mark_list)
            data[upk]["mark_min"] = min(mark_list)
            data[upk]["mark_median"] = round(statistics.median(mark_list), 1)
            data[upk]["mark_mean"] = round(statistics.mean(mark_list), 1)
            data[upk]["mark_mode"] = statistics.mode(mark_list)
            if len(mark_list) >= 2:
                data[upk]["mark_stdev"] = round(statistics.stdev(mark_list), 1)
            else:
                data[upk]["mark_stdev"] = "n/a"

        return data

    @transaction.atomic
    def get_mark_histogram_and_stats_by_versions(
        self, question: int
    ) -> Dict[int, Dict[str, Any]]:
        """Get marking histogram and stats for the given question separated by version.

        Args:
            question (int): The question

        Returns:
            dict (int, dict[str,any]): for each version give a dict that
            contains 'histogram', 'number', 'mark_max, 'mark_min',
            'mark_median', 'mark_mean', 'mark_mode', 'mark_stdev', 'remaining'.
        """
        data: Dict[int, Dict[str, Any]] = {}
        try:
            completed_tasks = MarkingTask.objects.filter(
                status=MarkingTask.COMPLETE,
                question_number=question,
            ).prefetch_related(
                "latest_annotation",
            )
        except MarkingTask.DoesNotExist:
            return data
        for X in completed_tasks:
            if X.question_version not in data:
                data[X.question_version] = {
                    "histogram": {
                        qm: 0
                        for qm in range(
                            SpecificationService.get_question_mark(question) + 1
                        )
                    },
                }
            data[X.question_version]["histogram"][X.latest_annotation.score] += 1

        for ver in data:
            mark_list = [
                key
                for key, value in data[ver]["histogram"].items()
                for _ in range(value)
            ]
            data[ver]["number"] = len(mark_list)
            data[ver]["mark_max"] = max(mark_list)
            data[ver]["mark_min"] = min(mark_list)
            data[ver]["mark_median"] = round(statistics.median(mark_list), 1)
            data[ver]["mark_mean"] = round(statistics.mean(mark_list), 1)
            data[ver]["mark_mode"] = statistics.mode(mark_list)
            if len(mark_list) >= 2:
                data[ver]["mark_stdev"] = round(statistics.stdev(mark_list), 1)
            else:
                data[ver]["mark_stdev"] = "n/a"
            # get remaining tasks by excluding COMPLETE and OUT_OF_DATE
            # TODO - can we optimise this a bit? one query per version is okay, but can likely do in 1.
            data[ver]["remaining"] = (
                MarkingTask.objects.exclude(status=MarkingTask.OUT_OF_DATE)
                .exclude(status=MarkingTask.COMPLETE)
                .filter(question_number=question, question_version=ver)
                .count()
            )

        return data

    @transaction.atomic
    def get_marking_task_annotation_info(self, question, version):
        task_info = {}
        for task in (
            MarkingTask.objects.exclude(status=MarkingTask.OUT_OF_DATE)
            .filter(question_number=question, question_version=version)
            .prefetch_related("latest_annotation", "paper", "assigned_user")
            .order_by("paper__paper_number")
        ):
            dat = {
                "status": task.get_status_display(),
            }
            if task.status == MarkingTask.COMPLETE:
                dat.update(
                    {
                        "username": task.assigned_user.username,
                        "score": task.latest_annotation.score,
                        "annotation_image": task.latest_annotation.image.pk,
                    }
                )

            task_info[task.paper.paper_number] = dat

        return task_info

    @transaction.atomic
    def filter_marking_task_annotation_info(
        self,
        paper_min=None,
        paper_max=None,
        score_min=None,
        score_max=None,
        question=None,
        version=None,
        username=None,
    ):
        task_set = MarkingTask.objects.exclude(status=MarkingTask.OUT_OF_DATE)
        if paper_min:
            task_set = task_set.filter(paper__paper_number__gte=paper_min)
        if paper_max:
            task_set = task_set.filter(paper__paper_number__lte=paper_max)
        if score_min:
            task_set = task_set.filter(latest_annotation__score__gte=score_min)
        if score_max:
            task_set = task_set.filter(latest_annotation__score__lte=score_max)
        if question:
            task_set = task_set.filter(question_number=question)
        if version:
            task_set = task_set.filter(question_version=version)
        if username:
            task_set = task_set.filter(assigned_user__username=username)
        task_info = {}
        for task in task_set.prefetch_related(
            "latest_annotation", "paper", "assigned_user"
        ).order_by("paper__paper_number"):
            dat = {
                "status": task.get_status_display(),
                "question": task.question_number,
                "version": task.question_version,
            }
            if task.status == MarkingTask.COMPLETE:
                dat.update(
                    {
                        "username": task.assigned_user.username,
                        "last_update": arrow.get(
                            task.latest_annotation.time_of_last_update
                        ).humanize(),
                        "score": task.latest_annotation.score,
                        "annotation_pk": task.latest_annotation.pk,
                    }
                )

            task_info[task.paper.paper_number] = dat

        return task_info

    @transaction.atomic
    def get_list_of_users_who_marked_anything(self):
        return [
            X.assigned_user.username
            for X in MarkingTask.objects.filter(status=MarkingTask.COMPLETE)
            .prefetch_related("assigned_user")
            .distinct("assigned_user")
        ]
