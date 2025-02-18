# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023-2024 Andrew Rechnitzer
# Copyright (C) 2024-2025 Colin B. Macdonald
# Copyright (C) 2024 Aidan Murphy
# Copyright (C) 2024 Bryan Tanady

import statistics
from typing import Any

import arrow
from numpy import histogram

from django.db import transaction

from plom.misc_utils import pprint_score

from Papers.services import SpecificationService
from ..models import MarkingTask, MarkingTaskTag


def generic_stats_dict_from_list(mark_list):
    stats_dict = {}
    stats_dict["mark_max"] = max(mark_list)
    stats_dict["mark_min"] = min(mark_list)
    stats_dict["mark_median"] = statistics.median(mark_list)
    stats_dict["mark_mean"] = statistics.mean(mark_list)
    stats_dict["mark_mode"] = statistics.mode(mark_list)

    stats_dict["mark_max_str"] = pprint_score(stats_dict["mark_max"])
    stats_dict["mark_min_str"] = pprint_score(stats_dict["mark_min"])
    stats_dict["mark_median_str"] = f"{stats_dict['mark_median']:.1f}"
    stats_dict["mark_mean_str"] = f"{stats_dict['mark_mean']:.1f}"
    stats_dict["mark_mode_str"] = pprint_score(stats_dict["mark_mode"])

    if len(mark_list) >= 2:
        stats_dict["mark_stdev"] = statistics.stdev(mark_list)
        stats_dict["mark_stdev_str"] = f"{stats_dict['mark_stdev']:.1f}"
    else:
        stats_dict["mark_stdev"] = stats_dict["mark_stdev_str"] = "n/a"

    return stats_dict


def score_histogram(score_list, max_score, min_score=0, bin_width=1):
    """Helper function to make histogram dicts."""
    bins = [edge for edge in range(min_score, max_score + bin_width, bin_width)]

    # np.histogram doesn't consider the rightmost edge as a separate bin
    bins.append(max_score)
    bin_values, _ = histogram(score_list, bins)
    # remove placeholder right bin edge
    bins.pop()

    return dict(zip(bins, list(map(int, bin_values))))


class MarkingStatsService:
    """Functions for getting marking stats."""

    @transaction.atomic
    def get_basic_marking_stats(
        self, question: int, *, version: int | None = None
    ) -> dict[str, Any]:
        """Send back current marking statistics for the given question + version.

        Args:
            question: the question to compute for

        Keyword Args:
            version: optionally, a specific version, or get for all versions if omitted.

        Returns:
            Dictionary containing the following, 'number_of_completed_tasks',
            'all_task_count', 'completed_percentage', 'mark_max',
            'mark_max_str', 'mark_min', 'mark_min_str', 'mark_median',
            'mark_median_str', 'mark_mean', 'mark_mean_str', 'mark_mode',
            'mark_mode_str', 'mark_stdev', 'mark_stdev_str', 'mark_full'
        """
        stats_dict = {
            "number_of_completed_tasks": 0,
            "all_task_count": 0,
            "completed_percentage": 0,
            "mark_max": 0,
            "mark_max_str": "n/a",
            "mark_min": 0,
            "mark_min_str": "n/a",
            "mark_median": 0,
            "mark_median_str": "n/a",
            "mark_mean": 0,
            "mark_mean_str": "n/a",
            "mark_mode": 0,
            "mark_mode_str": "n/a",
            "mark_stdev": "n/a",
            "mark_stdev_str": "n/a",
            "avg_marking_time": 0,
            "mark_full": SpecificationService.get_question_mark(question),
        }
        try:
            all_tasks = MarkingTask.objects.filter(question_index=question).exclude(
                status=MarkingTask.OUT_OF_DATE
            )
            completed_tasks = MarkingTask.objects.filter(
                status=MarkingTask.COMPLETE,
                question_index=question,
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
            stats_dict.update(generic_stats_dict_from_list(mark_list))
        return stats_dict

    @transaction.atomic
    def get_mark_histogram(
        self, question: int, *, version: int | None = None
    ) -> dict[int, int]:
        """Get the histogram of marks for the given question, version.

        Args:
            question: the question to compute for

        Keyword Args:
            version: optionally, a specific version, or get for all versions if omitted.

        Returns:
            The histogram as a dict of mark vs count.
        """
        max_question_mark = SpecificationService.get_question_mark(question)
        scores = []

        try:
            completed_tasks = MarkingTask.objects.filter(
                status=MarkingTask.COMPLETE,
                question_index=question,
            ).prefetch_related("latest_annotation")
            if version:
                completed_tasks = completed_tasks.filter(question_version=version)
        except MarkingTask.DoesNotExist:
            return score_histogram([], max_question_mark)
        for X in completed_tasks:
            scores.append(X.latest_annotation.score)

        hist = score_histogram(scores, max_question_mark)
        return hist

    @transaction.atomic
    def get_list_of_users_who_marked(
        self, question: int, *, version: int | None = None
    ) -> list[str]:
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
            question_index=question,
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
    ) -> dict[int, dict[str, Any]]:
        """Get marking histogram and stats for the given question/version separated by user.

        Args:
            question (int): The question
            version (int): The version

        Returns:
            dict (int, dict[str,any]): for each user-pk give a dict that
            contains 'username', 'histogram', 'scores', 'number',
            'mark_max', 'mark_max_str', 'mark_min', 'mark_min_str',
            'mark_median', 'mark_median_str', 'mark_mean', 'mark_mean_str',
            'mark_mode', 'mark_mode_str', 'mark_stdev', 'mark_stdev_str'.
        """
        data: dict[int, dict[str, Any]] = {}
        try:
            completed_tasks = MarkingTask.objects.filter(
                status=MarkingTask.COMPLETE,
                question_index=question,
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
                    "scores": [],
                }
            data[X.assigned_user.pk]["scores"].append(X.latest_annotation.score)

        for upk in data:
            mark_list = data[upk]["scores"]
            max_question_mark = SpecificationService.get_question_mark(question)
            data[upk]["histogram"] = score_histogram(mark_list, max_question_mark)
            data[upk]["number"] = len(mark_list)
            data[upk].update(generic_stats_dict_from_list(mark_list))
        return data

    @transaction.atomic
    def get_mark_histogram_and_stats_by_versions(
        self, question: int
    ) -> dict[int, dict[str, Any]]:
        """Get marking histogram and stats for the given question separated by version.

        Args:
            question (int): The question

        Returns:
            dict (int, dict[str,any]): for each version give a dict that
            contains 'histogram', 'scores', 'number', 'mark_max', 'mark_max_str',
            'mark_min', 'mark_min_str', 'mark_median', 'mark_median_str',
            'mark_mean','mark_mean_str', 'mark_mode','mark_mode_str',
            'mark_stdev','mark_stdev_str', 'remaining'.
        """
        data: dict[int, dict[str, Any]] = {}
        try:
            completed_tasks = MarkingTask.objects.filter(
                status=MarkingTask.COMPLETE,
                question_index=question,
            ).prefetch_related(
                "latest_annotation",
            )
        except MarkingTask.DoesNotExist:
            return data
        for X in completed_tasks:
            if X.question_version not in data:
                data[X.question_version] = {
                    "scores": [],
                }
            data[X.question_version]["scores"].append(X.latest_annotation.score)

        for ver in data:
            mark_list = data[ver]["scores"]
            max_question_mark = SpecificationService.get_question_mark(question)
            data[ver]["histogram"] = score_histogram(mark_list, max_question_mark)
            data[ver]["number"] = len(mark_list)
            data[ver].update(generic_stats_dict_from_list(mark_list))
            # get remaining tasks by excluding COMPLETE and OUT_OF_DATE
            # TODO - can we optimise this a bit? one query per version is okay, but can likely do in 1.
            data[ver]["remaining"] = (
                MarkingTask.objects.exclude(status=MarkingTask.OUT_OF_DATE)
                .exclude(status=MarkingTask.COMPLETE)
                .filter(question_index=question, question_version=ver)
                .count()
            )

        return data

    @transaction.atomic
    def get_marking_task_annotation_info(self, question, version):
        task_info = {}
        for task in (
            MarkingTask.objects.exclude(status=MarkingTask.OUT_OF_DATE)
            .filter(question_index=question, question_version=version)
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
                        "score_str": pprint_score(task.latest_annotation.score),
                        "annotation_image": task.latest_annotation.image.pk,
                    }
                )

            task_info[task.paper.paper_number] = dat

        return task_info

    @transaction.atomic
    def filter_marking_task_annotation_info(
        self,
        paper_min: int | None = None,
        paper_max: int | None = None,
        score_min: int | None = None,
        score_max: int | None = None,
        question_idx: int | None = None,
        version: int | None = None,
        username: str | None = None,
        the_tag: str | None = None,
        status: int | None = None,
    ) -> list[dict[str, Any]]:
        task_set = MarkingTask.objects.exclude(status=MarkingTask.OUT_OF_DATE)
        if paper_min:
            task_set = task_set.filter(paper__paper_number__gte=paper_min)
        if paper_max:
            task_set = task_set.filter(paper__paper_number__lte=paper_max)
        if score_min:
            task_set = task_set.filter(latest_annotation__score__gte=score_min)
        if score_max:
            task_set = task_set.filter(latest_annotation__score__lte=score_max)
        if question_idx:
            task_set = task_set.filter(question_index=question_idx)
        if version:
            task_set = task_set.filter(question_version=version)
        if username:
            task_set = task_set.filter(assigned_user__username=username)
        if the_tag:
            # if tag with this text exists then filter on it, else skip.
            try:
                tag_obj = MarkingTaskTag.objects.get(text=the_tag)
                task_set = task_set.filter(markingtasktag=tag_obj)
            except MarkingTaskTag.DoesNotExist:
                pass
        if status:
            task_set = task_set.filter(status=status)
        task_info = []
        for task in task_set.prefetch_related(
            "latest_annotation", "paper", "assigned_user"
        ).order_by("paper__paper_number"):
            dat = {
                "paper_number": task.paper.paper_number,
                "status": task.get_status_display(),
                "question": task.question_index,
                "version": task.question_version,
                "task_pk": task.pk,
            }
            all_tags = sorted([tag.text for tag in task.markingtasktag_set.all()])
            dat.update(
                {
                    "tags": [tg for tg in all_tags if tg[0] != "@"],
                    "attn_tags": [tg for tg in all_tags if tg[0] == "@"],
                }
            )
            if task.status == MarkingTask.COMPLETE:
                dat.update(
                    {
                        "username": task.assigned_user.username,
                        "last_update": arrow.get(
                            task.latest_annotation.time_of_last_update
                        ).humanize(),
                        "score": task.latest_annotation.score,
                        "score_str": pprint_score(task.latest_annotation.score),
                        "marking_time": task.latest_annotation.marking_time,
                        "integrity": str(task.pk),  # TODO: not implemented yet
                    }
                )
            elif task.status == MarkingTask.OUT:
                dat.update(
                    {
                        "username": task.assigned_user.username,
                        "integrity": str(task.pk),  # TODO: not implemented yet
                    }
                )

            task_info.append(dat)

        return task_info

    @transaction.atomic
    def get_list_of_users_who_marked_anything(self):
        return [
            X.assigned_user.username
            for X in MarkingTask.objects.filter(status=MarkingTask.COMPLETE)
            .prefetch_related("assigned_user")
            .distinct("assigned_user")
        ]
