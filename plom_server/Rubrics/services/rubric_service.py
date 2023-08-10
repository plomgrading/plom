# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2023 Brennen Chiu
# Copyright (C) 2019-2023 Colin B. Macdonald
# Copyright (C) 2019-2023 Andrew Rechnitzer
# Copyright (C) 2020 Dryden Wiebe
# Copyright (C) 2021 Nicholas J H Lai
# Copyright (C) 2023 Julian Lapenna
# Copyright (C) 2023 Divy Patel
# Copyright (C) 2023 Natalie Balashov

import html
import logging
from typing import Dict, List, Union

from operator import itemgetter

from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.db.models import QuerySet

from rest_framework.exceptions import ValidationError

from Mark.models import Annotation
from Mark.models.tasks import MarkingTask
from Papers.models import Paper
from Papers.services import SpecificationService
from ..serializers import (
    RubricSerializer,
)
from ..models import Rubric
from ..models import RubricPane


log = logging.getLogger("RubricServer")


class RubricService:
    """Class to encapsulate functions for creating and modifying rubrics."""

    __valid_kinds = ("absolute", "neutral", "relative")

    def create_rubric(self, rubric_data: Dict) -> Rubric:
        """Create a rubric using data submitted by a marker.

        Args:
            rubric_data: data for a rubric submitted by a web request.

        Returns:
            The created and saved rubric instance.

        Raises:
            KeyError: if rubric_data contains missing username or kind fields.
            ValidationError: if rubric kind is not a valid option.
            ValueError: if username does not exist in the DB.
        """
        # TODO: add a function to check if a rubric_data is valid/correct
        self.check_rubric(rubric_data)

        username = rubric_data.pop("username")
        try:
            user = User.objects.get(username=username)
            rubric_data["user"] = user.pk
        except ObjectDoesNotExist as e:
            raise ValueError(f"User {username} does not exist.") from e

        kind = rubric_data["kind"]

        if kind not in RubricService.__valid_kinds:
            raise ValidationError(f"Cannot make rubric of kind '{kind}'.")

        serializer = RubricSerializer(data=rubric_data)
        serializer.is_valid()
        serializer.save()
        rubric = serializer.instance

        return rubric

    @transaction.atomic
    def modify_rubric(self, key: str, rubric_data: Dict) -> Rubric:
        """Modify a rubric.

        Args:
            key: a sequence of ints that uniquely identify a specific rubric.
            rubric_data: data for a rubric submitted by a web request.

        Returns:
            The modified rubric instance.

        Exceptions:
            ValueError: wrong "kind" or invalid rubric data.
        """
        username = rubric_data.pop("username")
        user = User.objects.get(
            username=username
        )  # TODO: prevent different users from modifying rubrics?
        rubric_data["user"] = user.pk

        kind = rubric_data["kind"]

        if kind not in RubricService.__valid_kinds:
            raise ValidationError(f"Cannot make rubric of kind '{kind}'.")

        try:
            rubric = Rubric.objects.get(key=key)
            serializer = RubricSerializer(rubric, data=rubric_data)
            serializer.is_valid()
            serializer.save()
            rubric_instance = serializer.instance
        except ObjectDoesNotExist:
            raise ValidationError("No rubric exists.")

        return rubric_instance

    def get_rubrics(self, *, question: Union[None, str] = None) -> List[Dict]:
        """Get the rubrics, possibly filtered by question number.

        Args:
            question: question number or None for all.

        Returns:
            Collection of dictionaries, one for each rubric.
        """
        if question is None:
            rubric_list = Rubric.objects.all()
        else:
            rubric_list = Rubric.objects.filter(question=question)
        rubric_data = []

        for r in rubric_list.prefetch_related("user"):
            rubric_dict = {
                "id": r.key,
                "kind": r.kind,
                "display_delta": r.display_delta,
                "value": r.value,
                "out_of": r.out_of,
                "text": r.text,
                "tags": r.tags,
                "meta": r.meta,
                "username": r.user.username,
                "question": r.question,
                "versions": r.versions,
                "parameters": r.parameters,
            }
            rubric_data.append(rubric_dict)

        new_rubric_data = sorted(rubric_data, key=itemgetter("kind"))

        return new_rubric_data

    def get_all_rubrics(self) -> QuerySet[Rubric]:
        """Get all the rubrics lazily, so that lazy filtering is possible.

        See: https://docs.djangoproject.com/en/4.2/topics/db/queries/#querysets-are-lazy

        Returns:
            Lazy queryset of all rubrics.
        """
        return Rubric.objects.all()

    def init_rubrics(self, username: str) -> bool:
        """Add special rubrics such as deltas and per-question specific.

        Args:
            Username to associate with the initialized rubrics.

        Returns:
            True if initialized or False if it was already initialized.

        Exceptions:
            ValueError: username does not exist or is not part of the manager group.
        """
        try:
            user_obj = User.objects.get(
                username__iexact=username, groups__name="manager"
            )
        except ObjectDoesNotExist as e:
            raise ValueError(
                f"User '{username}' does not exist or has wrong permissions!"
            ) from e
        # TODO: legacy checks for specific "no answer given" rubric, see `db_create.py`
        existing_rubrics = Rubric.objects.all()
        if existing_rubrics:
            return False
        spec = SpecificationService.get_the_spec()
        self._build_special_rubrics(spec, username)
        return True

    def _build_special_rubrics(self, spec: Dict, username: str) -> None:
        log.info("Building special manager-generated rubrics")
        # create standard manager delta-rubrics - but no 0, nor +/- max-mark
        for q in range(1, 1 + spec["numberOfQuestions"]):
            mx = spec["question"]["{}".format(q)]["mark"]
            # make zero mark and full mark rubrics
            rubric = {
                "kind": "absolute",
                "display_delta": f"0 of {mx}",
                "value": "0",
                "out_of": mx,
                "text": "no answer given",
                "question": q,
                "meta": "Is this answer blank or nearly blank?  Please do not use "
                + "if there is any possibility of relevant writing on the page.",
                "tags": "",
                "username": username,
            }
            try:
                r = self.create_rubric(rubric)
            except AssertionError:
                print("Skipping absolute rubric, not implemented yet, Issue #2641")
            # log.info("Built no-answer-rubric Q%s: key %s", q, r.pk)

            rubric = {
                "kind": "absolute",
                "display_delta": f"0 of {mx}",
                "value": "0",
                "out_of": mx,
                "text": "no marks",
                "question": q,
                "meta": "There is writing here but its not sufficient for any points.",
                "tags": "",
                "username": username,
            }
            try:
                r = self.create_rubric(rubric)
            except AssertionError:
                print("Skipping absolute rubric, not implemented yet, Issue #2641")
            # log.info("Built no-marks-rubric Q%s: key %s", q, r.pk)

            rubric = {
                "kind": "absolute",
                "display_delta": f"{mx} of {mx}",
                "value": f"{mx}",
                "out_of": mx,
                "text": "full marks",
                "question": q,
                "meta": "",
                "tags": "",
                "username": username,
            }
            try:
                r = self.create_rubric(rubric)
            except AssertionError:
                print("Skipping absolute rubric, not implemented yet, Issue #2641")
            # log.info("Built full-marks-rubric Q%s: key %s", q, r.pk)

            # now make delta-rubrics
            for m in range(1, mx + 1):
                # make positive delta
                rubric = {
                    "display_delta": "+{}".format(m),
                    "value": m,
                    "out_of": 0,
                    "text": ".",
                    "kind": "relative",
                    "question": q,
                    "meta": "",
                    "tags": "",
                    "username": username,
                }
                r = self.create_rubric(rubric)
                log.info("Built delta-rubric +%d for Q%s: %s", m, q, r.pk)
                # make negative delta
                rubric = {
                    "display_delta": "-{}".format(m),
                    "value": -m,
                    "out_of": 0,
                    "text": ".",
                    "kind": "relative",
                    "question": q,
                    "meta": "",
                    "tags": "",
                    "username": username,
                }
                r = self.create_rubric(rubric)
                log.info("Built delta-rubric -%d for Q%s: %s", m, q, r.pk)

    def erase_all_rubrics(self) -> int:
        """Remove all rubrics, permanently deleting them.  BE CAREFUL.

        Returns:
            How many rubrics were removed.
        """
        n = 0
        for r in Rubric.objects.all():
            r.delete()
            n += 1
        return n

    def get_rubric_pane(self, user: User, question: int) -> Dict:
        """Gets a rubric pane for a user.

        Args:
            user: a User instance
            question: the question number

        Returns:
            dict: the JSON representation of the pane.
        """
        pane, created = RubricPane.objects.get_or_create(user=user, question=question)
        if created:
            return {}
        return pane.data

    def update_rubric_pane(self, user: User, question: int, data: Dict) -> None:
        """Updates a rubric pane for a user.

        Args:
            user: a User instance
            question: question number associated with the rubric pane
            data: dict representing the new pane
        """
        pane = RubricPane.objects.get(user=user, question=question)
        pane.data = data
        pane.save()

    def check_rubric(self, rubric_data: Dict) -> None:
        """Check rubric data to ensure the data is consistent.

        Args:
            rubric_data: data for a rubric submitted by a web request.
        """
        # if rubric_data["kind"] not in ["relative", "neutral", "absolute"]:
        #     raise ValidationError(f"Unrecognised rubric kind: {rubric_data.kind}")
        pass

    def get_annotation_from_rubric(self, rubric: Rubric) -> QuerySet[Annotation]:
        """Get the queryset of annotations that use this rubric.

        Args:
            Rubric instance

        Returns:
            A query of Annotation instances
        """
        return rubric.annotations.all()

    def get_rubrics_from_annotation(self, annotation: Annotation) -> QuerySet[Rubric]:
        """Get the queryset of rubrics that are used by this annotation.

        Args:
            annotation: Annotation instance

        Returns:
            Rubric instances
        """
        return Rubric.objects.filter(annotations=annotation)

    def get_rubrics_from_paper(self, paper_obj: Paper) -> QuerySet[Rubric]:
        """Get the queryset of rubrics that are used by this paper.

        Args:
            paper_obj: Paper instance

        Returns:
            Rubric instances
        """
        marking_tasks = MarkingTask.objects.filter(paper=paper_obj)
        annotations = Annotation.objects.filter(task__in=marking_tasks)
        rubrics = Rubric.objects.filter(annotations__in=annotations)
        return rubrics

    def get_rubrics_from_user(self, username: str) -> QuerySet[Rubric]:
        """Get the queryset of rubrics used by this user.

        Args:
            username: username of the user

        Returns:
            Rubric instances
        """
        user = User.objects.get(username=username)
        return Rubric.objects.filter(user=user)

    def get_all_annotations(self) -> QuerySet[Annotation]:
        """Gets all annotations.

        Returns:
            Lazy queryset of all rubrics.
        """
        return Annotation.objects.all()

    def get_rubric_as_html(self, rubric: Rubric) -> str:
        """Gets a rubric as HTML.

        Args:
            rubric: a Rubric instance

        Returns:
            HTML representation of the rubric.
        """
        text = html.escape(rubric.text)
        display_delta = html.escape(rubric.display_delta)
        return f"""
            <table style="color:#FF0000;">
                <tr>
                    <td style="padding:2px; border-width:1px; border-style:solid; border-color:#FF0000;">
                        <b>{display_delta}</b>
                    </td>
                    <td style="padding:2px; border-width:1px; border-style:dotted; border-color:#FF0000; border-left-style:None;">
                        {text}
                    </td>
                </tr>
            </table>
        """
