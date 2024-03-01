# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2023 Brennen Chiu
# Copyright (C) 2019-2024 Colin B. Macdonald
# Copyright (C) 2019-2023 Andrew Rechnitzer
# Copyright (C) 2020 Dryden Wiebe
# Copyright (C) 2021 Nicholas J H Lai
# Copyright (C) 2023 Julian Lapenna
# Copyright (C) 2023 Divy Patel
# Copyright (C) 2023 Natalie Balashov

from __future__ import annotations

import html
import logging
from typing import Any

from operator import itemgetter

from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
from django.db import transaction
from django.db.models import QuerySet

from rest_framework.exceptions import ValidationError

from Mark.models import Annotation
from Mark.models.tasks import MarkingTask
from Papers.models import Paper
from Papers.services import SpecificationService
from ..serializers import RubricSerializer
from ..models import Rubric
from ..models import RubricPane


log = logging.getLogger("RubricServer")


class RubricService:
    """Class to encapsulate functions for creating and modifying rubrics."""

    __valid_kinds = ("absolute", "neutral", "relative")

    def create_rubric(
        self, rubric_data: dict[str, Any], *, creating_user: User | None = None
    ) -> Rubric:
        """Create a rubric using data submitted by a marker.

        Args:
            rubric_data: data for a rubric submitted by a web request.

        Keyword Args:
            creating_user: who is trying to create the rubric.  ``None``
                means you don't care who (probably for internal use only).
                ``None`` also bypasses the rubric access settings.

        Returns:
            The created and saved rubric instance.

        Raises:
            KeyError: if rubric_data contains missing username or kind fields.
            ValidationError: if rubric kind is not a valid option.
            ValueError: if username does not exist in the DB.
            PermissionDenied: user are not allowed to create rubrics.
                This could be "this user" or "all users".
        """
        # TODO: add a function to check if a rubric_data is valid/correct
        self.check_rubric(rubric_data)

        username = rubric_data.pop("username")
        try:
            user = User.objects.get(username=username)
            rubric_data["user"] = user.pk
        except ObjectDoesNotExist as e:
            raise ValueError(f"User {username} does not exist.") from e

        # TODO: move this to Base?
        from Preparation.models import PapersPrintedSettingModel as SettingsModel

        s = SettingsModel.load()
        if creating_user is None:
            pass
        elif s.who_can_create_rubrics == "permissive":
            pass
        elif s.who_can_create_rubrics == "locked":
            raise PermissionDenied(
                "No users are allowed to create rubrics on this server"
            )
        else:
            # TODO: consult per-user permissions (not implemented yet)
            pass

        kind = rubric_data["kind"]
        if kind not in RubricService.__valid_kinds:
            raise ValidationError(f"Cannot make rubric of kind '{kind}'.")

        serializer = RubricSerializer(data=rubric_data)
        serializer.is_valid()
        serializer.save()
        rubric = serializer.instance

        return rubric

    @transaction.atomic
    def modify_rubric(
        self,
        key: str,
        rubric_data: dict[str, Any],
        *,
        modifying_user: User | None = None,
    ) -> Rubric:
        """Modify a rubric.

        Args:
            key: a sequence of ints that uniquely identify a specific rubric.
            rubric_data: data for a rubric submitted by a web request.

        Keyword Args:
            modifying_user: who is trying to modify the rubric.  This might
                differ from the "owner" of the rubric, i.e., the ``username``
                field inside the ``rubric_data``.  If you pass None (default)
                no checking will be done (probably for internal use).

        Returns:
            The modified rubric instance.

        Exceptions:
            ValueError: wrong "kind" or invalid rubric data.
            PermissionDenied: user does not have permission to modify.
                This could be "this user" or "all users".
        """
        user = User.objects.get(username=rubric_data.pop("username"))
        rubric_data["user"] = user.pk

        # TODO: move this to Base?
        from Preparation.models import PapersPrintedSettingModel as SettingsModel

        s = SettingsModel.load()
        if modifying_user is None:
            pass
        elif s.who_can_modify_rubrics == "permissive":
            pass
        elif s.who_can_modify_rubrics == "locked":
            raise PermissionDenied(
                "No users are allowed to modify rubrics on this server"
            )
        else:
            # TODO: consult per-user permissions (not implemented yet)
            # For now, we have only the default case: users can modify their own rubrics
            if user != modifying_user:
                raise PermissionDenied(
                    f'You ("{modifying_user}") are not allowed to modify'
                    f' rubrics created by other users (here "{user}")'
                )

        kind = rubric_data["kind"]
        if kind not in RubricService.__valid_kinds:
            raise ValidationError(f"Cannot make rubric of kind '{kind}'.")

        rubric = Rubric.objects.filter(key=key).select_for_update().get()
        serializer = RubricSerializer(rubric, data=rubric_data)
        serializer.is_valid()
        serializer.save()
        rubric_instance = serializer.instance
        return rubric_instance

    def get_rubrics(self, *, question: str | None = None) -> list[dict[str, Any]]:
        """Get the rubrics, possibly filtered by question number.

        Keyword Args:
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
            _ = User.objects.get(username__iexact=username, groups__name="manager")
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

    def _build_special_rubrics(self, spec: dict[str, Any], username: str) -> None:
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
        with transaction.atomic():
            for r in Rubric.objects.all().select_for_update():
                r.delete()
                n += 1
        return n

    def get_rubric_pane(self, user: User, question: int) -> dict:
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

    def update_rubric_pane(self, user: User, question: int, data: dict) -> None:
        """Updates a rubric pane for a user.

        Args:
            user: a User instance
            question: question number associated with the rubric pane
            data: dict representing the new pane
        """
        pane = RubricPane.objects.get(user=user, question=question)
        pane.data = data
        pane.save()

    def check_rubric(self, rubric_data: dict[str, Any]) -> None:
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

    def get_marking_tasks_with_rubric_in_latest_annotation(
        self, rubric: Rubric
    ) -> QuerySet[MarkingTask]:
        """Get the queryset of marking tasks that use this rubric in their latest annotations.

        Args:
            Rubric instance

        Returns:
            A query of MarkingTask instances
        """
        return (
            MarkingTask.objects.filter(
                status=MarkingTask.COMPLETE, latest_annotation__rubric__id=rubric.pk
            )
            .order_by("paper__paper_number")
            .prefetch_related("paper", "assigned_user", "latest_annotation")
        )

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
