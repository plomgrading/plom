# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Brennen Chiu
# Copyright (C) 2023-2025 Colin B. Macdonald
# Copyright (C) 2024 Bryan Tanady

from datetime import timedelta
from typing import Any

import arrow

from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.db.models.query import QuerySet
from django.utils import timezone

from plom_server.Mark.models import Annotation, MarkingTask
from plom_server.Mark.services import MarkingTaskService

from plom_server.UserManagement.models import Quota


class UserInfoServices:
    """Functions for User Info HTML page."""

    @classmethod
    @transaction.atomic
    def get_user_progress(cls, *, username: str) -> dict[str, Any]:
        """Get marking progress of a user.

        Args:
            username: the user's username.

        Returns:
            A dict whose keys are "tasks_claimed", "tasks_marked",
            "user_has_quota_limit", "user_quota_limit".
        """
        tasks_marked, tasks_claimed = cls.get_total_annotated_and_claimed_count_by_user(
            username
        )

        try:
            limit = Quota.objects.get(user__username=username).limit
            has_limit = True
        except ObjectDoesNotExist:
            limit = None
            has_limit = False

        data = {
            "user_tasks_claimed": tasks_claimed,
            "user_tasks_marked": tasks_marked,
            "user_has_quota_limit": has_limit,
            "user_quota_limit": limit,
        }
        return data

    @classmethod
    @transaction.atomic
    def get_all_user_progress(cls) -> dict[str, dict[str, Any]]:
        """Get marking progress for all users.

        Returns:
            A dict keyed by usernames, with values as in :method:`get_user_progress`.
        """
        # get everything from DB first, then we can do loops to assemble...

        # this will be missing keys for users that haven't claimed or marked
        complete_claimed_task_dict = (
            cls.get_total_annotated_and_claimed_count_by_users()
        )

        # this one will be missing all those without quota
        quota_limits_dict = {
            q.user.username: q.limit for q in Quota.objects.select_related("user").all()
        }

        # user_objs = User.objects.all().order_by("id")
        user_objs = User.objects.filter(groups__name__in=["marker"]).order_by("id")

        default_limit = Quota.default_limit

        # Now loop over filling in missing data
        data = {}
        for user in user_objs:
            try:
                tasks_marked, tasks_claimed = complete_claimed_task_dict[user.username]
            except KeyError:
                # User hasn't marked nor claimed any paper yet:
                tasks_marked, tasks_claimed = 0, 0

            try:
                limit = quota_limits_dict[user.username]
                has_limit = True
                would_exceed_default_limit = None
            except KeyError:
                has_limit = False
                limit = None
                would_exceed_default_limit = tasks_marked > default_limit

            data[user.username] = {
                "tasks_claimed": tasks_claimed,
                "tasks_marked": tasks_marked,
                "has_quota_limit": has_limit,
                "quota_limit": limit,
                "would_exceed_default_limit": would_exceed_default_limit,
            }

        return data

    @staticmethod
    def annotation_exists() -> bool:
        """Return True if there are any annotations in the database.

        Returns:
            True if there are annotations or False if there aren't any.

        Note: currently unused (and untested).
        """
        return Annotation.objects.exists()

    @classmethod
    def get_total_annotated_and_claimed_count_by_user(
        cls, username: str
    ) -> tuple[int, int]:
        """Retrieve count of complete and total claimed by a particular username.

        "Claimed tasks" are those tasks associated with the user with status OUT or Complete.

        Returns:
            A tuple of the count of the complete and claimed tasks.

        Raises:
            Not expected to raise any exceptions.
        """
        complete = (
            MarkingTaskService()
            .get_latest_annotations_from_complete_marking_tasks()
            .filter(user__username=username)
            .count()
        )

        claimed = complete + cls.get_total_claimed_but_unmarked_task_by_a_user(username)
        return (complete, claimed)

    @classmethod
    @transaction.atomic
    def get_total_annotated_and_claimed_count_by_users(
        cls,
    ) -> dict[str, tuple[int, int]]:
        """Retrieve count of complete and total claimed by users.

        "Claimed tasks" are those tasks associated with the user with status OUT or Complete.

        Returns:
            A dictionary mapping the marker to a tuple of the count of the complete and claimed tasks respectively.

        Raises:
            Not expected to raise any exceptions.
        """
        result = dict()

        markers_and_managers = User.objects.filter(
            groups__name__in=["marker"]
        ).order_by("groups__name", "username")

        annotation_count_dict: dict[str, int] = {
            user.username: 0 for user in markers_and_managers
        }
        annotations = (
            MarkingTaskService().get_latest_annotations_from_complete_marking_tasks()
        )
        annotations = annotations.prefetch_related("user")
        for annotation in annotations:
            if annotation.user.username in annotation_count_dict:
                annotation_count_dict[annotation.user.username] += 1

        for usr in annotation_count_dict:
            complete_task = annotation_count_dict[usr]
            claimed_task = (
                complete_task + cls.get_total_claimed_but_unmarked_task_by_a_user(usr)
            )
            result[usr] = (complete_task, claimed_task)

        return result

    @staticmethod
    def get_total_claimed_but_unmarked_task_by_a_user(username: str) -> int:
        """Retrieve the number of tasks claimed but unmarked by a user.

        These retrieve the tasks claimed by the users that have MarkingTask status of OUT.

        Args:
            username: user's username

        Returns:
            number of tasks claimed by the user whose status is still 'OUT'.
        """
        return MarkingTask.objects.filter(
            assigned_user__username=username, status=MarkingTask.OUT
        ).count()

    @transaction.atomic
    def get_annotations_based_on_user(
        self, annotations
    ) -> dict[str, dict[tuple[int, int], dict[str, int | str]]]:
        """Retrieve annotations based on the combination of user, question index, and version.

        Returns:
            A dictionary with usernames as keys, and nested dictionaries
            as values containing the count of annotations and average
            marking time for each (question index, question version)
            combination.
        """
        count_data: dict[str, dict[tuple[int, int], int]] = dict()
        total_marking_time_data: dict[str, dict[tuple[int, int], int]] = dict()

        for annotation in annotations:
            key = (annotation.task.question_index, annotation.task.question_version)
            count_data.setdefault(annotation.user.username, {}).setdefault(key, 0)
            count_data[annotation.user.username][key] += 1

            total_marking_time_data.setdefault(annotation.user.username, {}).setdefault(
                key, 0
            )
            total_marking_time_data[annotation.user.username][
                key
            ] += annotation.marking_time

        grouped_by_user: dict[str, dict[tuple[int, int], dict[str, int | str]]] = dict()

        for user in count_data:
            grouped_by_user[user] = dict()
            for key in count_data[user]:
                count = count_data[user][key]
                total_marking_time = total_marking_time_data[user][key]

                if total_marking_time is None:
                    total_marking_time = 0

                average_marking_time = round(
                    total_marking_time / count if count > 0 else 0
                )

                grouped_by_user[user][key] = {
                    "annotations_count": count,
                    "average_marking_time": self.seconds_to_humanize_time(
                        average_marking_time
                    ),
                    "percentage_marked": int(
                        (
                            count
                            / self._get_marking_task_count_based_on_question_and_version(
                                question=key[0], version=key[1]
                            )
                        )
                        * 100
                    ),
                    "date_format": arrow.utcnow()
                    .shift(seconds=average_marking_time)
                    .format("YYYYMMDDHHmmss"),
                }

        return grouped_by_user

    def get_annotations_based_on_question_and_version(
        self,
        grouped_by_user_annotations: dict[
            str, dict[tuple[int, int], dict[str, int | str]]
        ],
    ) -> dict[tuple[int, int], dict[str, list]]:
        """Group annotations by question index and version.

        Args:
            grouped_by_user_annotations: A dictionary with usernames as keys,
                and nested dictionaries as values containing the count
                of annotations and average marking time for each
                (question_index, question_version) combination.

        Returns:
            A dictionary containing annotations grouped by
            question indices and versions, with marker information and
            other data.
        """
        grouped_by_question: dict[tuple[int, int], dict[str, list]] = dict()

        for marker, annotation_data in grouped_by_user_annotations.items():
            for question, question_data in annotation_data.items():
                if question not in grouped_by_question:
                    grouped_by_question[question] = {
                        "annotations": [],
                    }
                grouped_by_question[question]["annotations"].append(
                    {
                        "marker": marker,
                        "annotations_count": question_data["annotations_count"],
                        "average_marking_time": question_data["average_marking_time"],
                        "percentage_marked": question_data["percentage_marked"],
                        "date_format": question_data["date_format"],
                    }
                )

        return grouped_by_question

    def seconds_to_humanize_time(self, seconds: float) -> str:
        """Convert the given number of seconds to a human-readable time string.

        Args:
            seconds: the number of seconds, unsigned so no distinction
                is made between past and future.

        Returns:
            A human-readable time string.
        """
        if seconds > 9:
            return arrow.utcnow().shift(seconds=seconds).humanize(only_distance=True)
        else:
            return (
                arrow.utcnow()
                .shift(seconds=seconds)
                .humanize(only_distance=True, granularity=["second"])
            )

    @transaction.atomic
    def _get_marking_task_count_based_on_question_and_version(
        self, question: int, version: int
    ) -> int:
        """Get the count of MarkingTasks based on the given question index and version.

        Args:
            question: which question by 1-based index.
            version: which question version.

        Returns:
            The count of MarkingTask for the specific question index and version.
        """
        return MarkingTask.objects.filter(
            question_index=question, question_version=version
        ).count()

    @transaction.atomic
    def filter_annotations_by_time_delta_seconds(
        self, time_delta_seconds: int
    ) -> QuerySet[Annotation]:
        """Filter annotations by time in seconds.

        Args:
            time_delta_seconds: (int) Number of seconds.

        Returns:
            QuerySet: Filtered queryset of annotations.
        """
        annotations = (
            MarkingTaskService().get_latest_annotations_from_complete_marking_tasks()
        )

        if time_delta_seconds == 0:
            return annotations
        else:
            time_interval_start = timezone.now() - timedelta(seconds=time_delta_seconds)
            return annotations.filter(time_of_last_update__gte=time_interval_start)

    @transaction.atomic
    def get_time_of_latest_updated_annotation(self) -> str:
        """Get the human readable time of the latest updated annotation.

        Returns:
            Human-readable time of the latest updated annotation or
            the string ``"never"`` if there have not been any annotations.
        """
        try:
            annotations = (
                MarkingTaskService().get_latest_annotations_from_complete_marking_tasks()
            )
            latest_annotation = annotations.latest("time_of_last_update")
        except ObjectDoesNotExist:
            return "never"
        return arrow.get(latest_annotation.time_of_last_update).humanize()
