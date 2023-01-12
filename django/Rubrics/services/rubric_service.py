# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates

from django.contrib.auth.models import User

from Rubrics.serializers import RelativeRubricSerializer
from Rubrics.models import RelativeRubric, RubricPane


class RubricService:
    """
    Class to encapsulate functions for creating and modifying rubrics.
    """

    def create_rubric(self, rubric_data):
        """
        Create a rubric using data submitted by a marker.

        Args:
            rubric_data: (dict) data for a rubric submitted by a web request.

        Returns:
            Rubric: the created and saved rubric instance.
        """

        username = rubric_data.pop("username")
        user = User.objects.get(username=username)
        rubric_data["user"] = user.pk

        kind = rubric_data.pop("kind")
        if kind != "relative":
            # TODO: Other rubric types not implemented in Django yet
            raise NotImplementedError()

        rubric_data.pop("versions")  # TODO: rubric scope not implemented yet

        serializer = RelativeRubricSerializer(data=rubric_data)
        serializer.is_valid()
        print(serializer.errors)
        serializer.save()

        rubric = serializer.instance
        return rubric

    def modify_rubric(self, key, rubric_data):
        """
        Modify a rubric.

        Args:
            key: (str) a sequence of ints representing
            rubric_data: (dict) data for a rubric submitted by a web request.

        Returns:
            Rubric: the modified rubric instance.
        """

        username = rubric_data.pop("username")
        user = User.objects.get(
            username=username
        )  # TODO: prevent different users from modifying rubrics?
        rubric_data["user"] = user.pk

        kind = rubric_data.pop("kind")
        if kind != "relative":
            # TODO: Other rubric types not implemented in Django yet
            raise NotImplementedError()

        rubric_data.pop("versions")  # TODO: rubric scope not implemented yet

        rubric = RelativeRubric.objects.get(key=key)
        serializer = RelativeRubricSerializer(rubric, data=rubric_data)
        serializer.is_valid()
        serializer.save()

        return serializer.instance

    def get_rubric_pane(self, user, question):
        """
        Gets a rubric pane for a user.

        Args:
            user: a User instance
            question: (int)

        Returns:
            dict: the JSON representation of the pane.
        """

        pane, created = RubricPane.objects.get_or_create(
            user=user, question=question
        )  # TODO: have a default pane instead of a blank one?
        if created:
            return {}
        return pane.data

    def update_rubric_pane(self, user, question, data):
        """
        Updates a rubric pane for a user.

        Args:
            user: a User isntance
            question: int
            data: dict representing the new pane
        """

        pane = RubricPane.objects.get(user=user, question=question)
        pane.data = data
        pane.save()
