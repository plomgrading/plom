# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Andrew Rechnitzer

import statistics

from django.db import transaction
from django.contrib.auth.models import User

from Papers.services import SpecificationService
from ..models import (
    MarkingTask,
)


class MarkingStatsService:
    """Functions for getting marking stats."""

    @transaction.atomic
    def get_basic_marking_stats(self, version, question, user_obj=None):
        """Send back current marking progress counts to the client.

        Args:
            question (int)
            version (int)
            user_obj (User)

        Returns:
            Dict
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
            "mark_stddev": 0,
            "avg_marking_time": 0,
            "mark_full": SpecificationService.get_question_mark(question),
        }

        try:
            all_task_count = (
                MarkingTask.objects.filter(
                    question_number=question, question_version=version
                )
                .exclude(status=MarkingTask.OUT_OF_DATE)
                .count()
            )

            completed_tasks = MarkingTask.objects.filter(
                status=MarkingTask.COMPLETE,
                question_number=question,
                question_version=version,
            ).prefetch_related("latest_annotation")

            if user_obj:
                completed_tasks.filter(assigned_user=user_obj)

        except MarkingTask.DoesNotExist:
            return stats_dict

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
            stats_dict["mark_stdev"] = round(statistics.stdev(mark_list), 1)

        return stats_dict

    @transaction.atomic
    def get_mark_histogram(self, version, question):
        hist = {
            qm: 0 for qm in range(SpecificationService.get_question_mark(question) + 1)
        }
        try:
            completed_tasks = MarkingTask.objects.filter(
                status=MarkingTask.COMPLETE,
                question_number=question,
                question_version=version,
            ).prefetch_related("latest_annotation")
        except MarkingTask.DoesNotExist:
            return hist
        for X in completed_tasks:
            hist[X.latest_annotation.score] += 1
        return hist

    @transaction.atomic
    def get_list_of_users_who_marked(self, question, version):
        return [
            X.assigned_user.username
            for X in MarkingTask.objects.filter(
                status=MarkingTask.COMPLETE,
                question_number=question,
                question_version=version,
            )
            .prefetch_related("assigned_user")
            .distinct("assigned_user")
        ]

    @transaction.atomic
    def get_mark_histogram_and_stats_by_users(self, version, question):
        data = {}
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
            data[upk]["mark_stdev"] = round(statistics.stdev(mark_list), 1)

        return data
