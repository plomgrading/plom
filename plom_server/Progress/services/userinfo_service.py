# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Brennen Chiu

from typing import Dict, Tuple

from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Count

from Mark.models import Annotation


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
    def get_total_annotations_based_on_user(self) -> Dict[User, int]:
        """Retrieve annotations based on user.

        Returns:
            Dict: A dictionary of all annotations(Value) corresponding with the markers(key).

        Raises:
            Not expected to raise any exceptions.
        """
        markers = User.objects.filter(groups__name="marker").order_by("username")
        annotation_data = markers.annotate(annotation_count=Count("annotation"))
        annotation_data_dict: Dict[User, int] = {
            marker: marker.annotation_count for marker in annotation_data
        }

        return annotation_data_dict

    @transaction.atomic
    def get_annotations_based_on_user_and_question_number_version(
        self,
    ) -> Dict[User, Dict[Tuple[int, int], int]]:
        """Retrieve annotations based on the combination of user, question number, and version.

        Returns a dictionary with users as keys and nested dictionaries as values.
        The nested dictionaries have a tuple (question_number, question_version) as keys
        and the count of annotations as values.

        Returns:
            Dict[User, Dict[Tuple[int, int], int]]: A dictionary with users as keys, and nested
                dictionaries as values containing the count of annotations for each
                (question_number, question_version) combination.
        """
        users = User.objects.prefetch_related("annotation_set").all()

        grouped_annotations = {}
        for user in users:
            for annotation in user.annotation_set.all():
                key = (
                    annotation.task.question_number,
                    annotation.task.question_version,
                )
                if user not in grouped_annotations:
                    grouped_annotations[user] = {}
                if key not in grouped_annotations[user]:
                    grouped_annotations[user][key] = 0
                grouped_annotations[user][key] += 1

        return grouped_annotations
