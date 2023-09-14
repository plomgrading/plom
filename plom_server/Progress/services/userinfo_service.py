# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Brennen Chiu
# Copyright (C) 2023 Colin B. Macdonald

from datetime import timedelta
from typing import Dict, Tuple, Union

import arrow

from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.db.models.query import QuerySet
from django.utils import timezone

from Mark.models import Annotation, MarkingTask
from Mark.services import MarkingTaskService


class UserInfoServices:
    """Functions for User Info HTML page."""

    @transaction.atomic
    def annotation_exists(self) -> bool:
        """Return True if there are any annotations in the database.

        Returns:
            bool : True if there are annotations or
                False if there aren't any
        """
        return Annotation.objects.exists()

    @transaction.atomic
    def get_total_annotations_count_based_on_user(self) -> Dict[str, int]:
        """Retrieve annotations based on user.

        Returns:
            Dict[str, int]: A dictionary of all annotations(Value) corresponding with the markers(key).

        Raises:
            Not expected to raise any exceptions.
        """
        annotations = (
            MarkingTaskService().get_latest_annotations_from_complete_marking_tasks()
        )
        markers_and_managers = User.objects.filter(
            groups__name__in=["marker"]
        ).order_by("groups__name", "username")
        annotation_count_dict: Dict[str, int] = {
            user.username: 0 for user in markers_and_managers
        }

        for annotation in annotations:
            if annotation.user.username in annotation_count_dict:
                annotation_count_dict[annotation.user.username] += 1

        return annotation_count_dict

    @transaction.atomic
    def get_annotations_based_on_user(
        self, annotations
    ) -> Dict[str, Dict[Tuple[int, int], Dict[str, Union[int, str]]]]:
        """Retrieve annotations based on the combination of user, question number, and version.

        Returns a dictionary with users as keys and nested dictionaries as values.
        The nested dictionaries have a tuple (question_number, question_version) as keys
        and the count of annotations and average marking time as values.

        Returns:
            Dict[str, Dict[Tuple[int, int], Dict[str, Union(int, str)]]]: A dictionary with users
                as keys, and nested dictionaries as values containing the count of annotations
                and average marking time for each (question_number, question_version) combination.
        """
        count_data: Dict[str, Dict[Tuple[int, int], int]] = dict()
        total_marking_time_data: Dict[str, Dict[Tuple[int, int], int]] = dict()

        for annotation in annotations:
            key = (annotation.task.question_number, annotation.task.question_version)
            count_data.setdefault(annotation.user.username, {}).setdefault(key, 0)
            count_data[annotation.user.username][key] += 1

            total_marking_time_data.setdefault(annotation.user.username, {}).setdefault(
                key, 0
            )
            total_marking_time_data[annotation.user.username][
                key
            ] += annotation.marking_time

        grouped_by_user: Dict[
            str, Dict[Tuple[int, int], Dict[str, Union[int, str]]]
        ] = dict()

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
                            / self.get_marking_task_count_based_on_question_number_and_version(
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

    def get_annotations_based_on_question_number_version(
        self,
        grouped_by_user_annotations: Dict[
            str, Dict[Tuple[int, int], Dict[str, Union[int, str]]]
        ],
    ) -> Dict[Tuple[int, int], Dict[str, list]]:
        """Group annotations by question number and version.

        Args:
            grouped_by_user_annotations: (Dict[str, Dict[Tuple[int, int], Dict[str, Union[int, str]]]])
                A dictionary with users as keys, and nested dictionaries as values containing the count
                of annotations and average marking time for each (question_number, question_version)
                combination.

        Returns:
            Dict[Tuple[int, int], Dict[str, list]]: A dictionary containing annotations grouped by
                question numbers and versions, with marker information and other data.
        """
        grouped_by_question: Dict[Tuple[int, int], Dict[str, list]] = dict()

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
    def get_marking_task_count_based_on_question_number_and_version(
        self, question: int, version: int
    ) -> int:
        """Get the count of MarkingTasks based on the given question number and version.

        Args:
            question: (int) The question number.
            version: (int) The question version.

        Returns:
            int: The count of MarkingTask for the specific question number and version.
        """
        return MarkingTask.objects.filter(
            question_number=question, question_version=version
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
