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
# Copyright (C) 2024 Aden Chan
# Copyright (C) 2024 Bryan Tanady

from __future__ import annotations

import html
import logging
from typing import Any, List

from operator import itemgetter

from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
from django.db import transaction
from django.db.models import QuerySet

from rest_framework.exceptions import ValidationError

from plom.plom_exceptions import PlomConflict
from Base.models import SettingsModel
from Mark.models import Annotation
from Mark.models.tasks import MarkingTask
from Papers.models import Paper
from Papers.services import SpecificationService
from ..serializers import RubricSerializer
from ..models import Rubric
from ..models import RubricPane


log = logging.getLogger("RubricServer")


def _Rubric_to_dict(r: Rubric) -> dict[str, Any]:
    return {
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
        "system_rubric": r.system_rubric,
        "published": r.published,
        "last_modified": r.last_modified,
        "modified_by_username": (
            None if not r.modified_by_user else r.modified_by_user.username
        ),
        "revision": r.revision,
    }


class RubricService:
    """Class to encapsulate functions for creating and modifying rubrics."""

    def create_rubric(
        self, rubric_data: dict[str, Any], *, creating_user: User | None = None
    ) -> dict[str, Any]:
        """Create a rubric using data submitted by a marker.

        Args:
            rubric_data: data for a rubric submitted by a web request.
                This input will not be modified by this call.

        Keyword Args:
            creating_user: who is trying to create the rubric.  ``None``
                means you don't care who (probably for internal use only).
                ``None`` also bypasses the rubric access settings.

        Returns:
            The new rubric data, in dict key-value format.

        Raises:
            KeyError: if rubric_data contains missing username or kind fields.
            ValidationError: if rubric kind is not a valid option.
            ValueError: if username does not exist in the DB.
            PermissionDenied: user are not allowed to create rubrics.
                This could be "this user" or "all users".
        """
        rubric_obj = self._create_rubric(rubric_data, creating_user=creating_user)
        return _Rubric_to_dict(rubric_obj)

    # implementation detail of the above, independently testable
    def _create_rubric(
        self, rubric_data: dict[str, Any], *, creating_user: User | None = None
    ) -> Rubric:
        rubric_data = rubric_data.copy()

        username = rubric_data.pop("username")
        try:
            user = User.objects.get(username=username)
            rubric_data["user"] = user.pk
            rubric_data["modified_by_user"] = user.pk
        except ObjectDoesNotExist as e:
            raise ValueError(f"User {username} does not exist.") from e

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

        rubric_data["latest"] = True
        serializer = RubricSerializer(data=rubric_data)
        if serializer.is_valid():
            serializer.save()
            rubric_obj = serializer.instance
            return rubric_obj
        else:
            raise ValidationError(serializer.errors)

    @transaction.atomic
    def modify_rubric(
        self,
        key: str,
        new_rubric_data: dict[str, Any],
        *,
        modifying_user: User | None = None,
    ) -> dict[str, Any]:
        """Modify a rubric.

        Args:
            key: a string that uniquely identify a specific rubric.
                Generally not the same as the "private key" used
                internally, although this could change in the future.
            rubric_data: data for a rubric submitted by a web request.
                This input will not be modified by this call.

        Keyword Args:
            modifying_user: who is trying to modify the rubric.  This might
                differ from the "owner" of the rubric, i.e., the ``username``
                field inside the ``rubric_data``.  If you pass None (default)
                no checking will be done (probably for internal use).

        Returns:
            The modified rubric data, in dict key-value format.

        Exceptions:
            ValueError: wrong "kind" or invalid rubric data.
            PermissionDenied: user does not have permission to modify.
                This could be "this user" or "all users".
            ValidationError: invalid kind, maybe other invalidity.
            PlomConflict: the new data is too old; someone else modified.
        """
        new_rubric_data = new_rubric_data.copy()
        username = new_rubric_data.pop("username")

        try:
            user = User.objects.get(username=username)
            new_rubric_data["user"] = user.pk
        except ObjectDoesNotExist as e:
            raise ValueError(f"User {username} does not exist.") from e

        try:
            rubric = (
                Rubric.objects.filter(key=key, latest=True).select_for_update().get()
            )
        except Rubric.DoesNotExist as e:
            raise ValueError(f"Rubric {key} does not exist.") from e

        # default revision if missing from incoming data
        new_rubric_data.setdefault("revision", 0)

        # incoming revision is not incremented to check if what the
        # revision was based on is outdated
        if not new_rubric_data["revision"] == rubric.revision:
            # TODO: record who last modified and when
            raise PlomConflict(
                f'The rubric your revision was based upon {new_rubric_data["revision"]} '
                f"does not match database content (revision {rubric.revision}): "
                f"most likely your  edits have collided with those of someone else."
            )

        # Generally, omitting modifying_user bypasses checks
        if modifying_user is None:
            pass
        elif rubric.system_rubric:
            raise PermissionDenied(
                f'User "{modifying_user}" is not allowed to modify system rubrics'
            )

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

        new_rubric_data.pop("modified_by_username", None)

        if modifying_user is not None:
            new_rubric_data["modified_by_user"] = modifying_user.pk

        new_rubric_data["revision"] += 1
        new_rubric_data["latest"] = True
        new_rubric_data["key"] = rubric.key
        serializer = RubricSerializer(data=new_rubric_data)

        if not serializer.is_valid():
            raise ValidationError(serializer.errors)

        rubric.latest = False
        rubric.save()

        serializer.save()
        rubric_obj = serializer.instance
        return _Rubric_to_dict(rubric_obj)

    def get_rubrics_as_dicts(
        self, *, question: int | None = None
    ) -> list[dict[str, Any]]:
        """Get the rubrics, possibly filtered by question.

        Keyword Args:
            question: question index or ``None`` for all.

        Returns:
            Collection of dictionaries, one for each rubric.
        """
        if question is None:
            rubric_list = Rubric.objects.all()
        else:
            rubric_list = Rubric.objects.filter(question=question)
        rubric_data = []

        for r in rubric_list.prefetch_related("user"):
            rubric_data.append(_Rubric_to_dict(r))

        new_rubric_data = sorted(rubric_data, key=itemgetter("kind"))

        return new_rubric_data

    def get_all_rubrics(self) -> QuerySet[Rubric]:
        """Get all the rubrics lazily, so that lazy filtering is possible.

        See: https://docs.djangoproject.com/en/4.2/topics/db/queries/#querysets-are-lazy

        Returns:
            Lazy queryset of all rubrics.
        """
        return Rubric.objects.filter(latest=True)

    def get_rubric_count(self) -> int:
        """How many rubrics in total (excluding revisions)."""
        return Rubric.objects.filter(latest=True).count()

    def get_rubric_by_key(self, rubric_key: str) -> Rubric:
        """Get the latest rurbic revision by its key/id.

        Args:
            rubric_key: which rubric.  Note currently the key/id is not
                the same as the internal ``pk``.

        Returns:
            The rubric object.  It is not "selected for update" so should
            be read-only.
        """
        return Rubric.objects.get(key=rubric_key, latest=True)

    def get_past_revisions_by_key(self, rubric_key: str) -> List[Rubric]:
        """Get all rubrics by it's key.

        Args:
            rubric_key (str): the key of the rubric.

        Returns:
            A list of rubrics with the specified key
        """
        return list(Rubric.objects.filter(key=rubric_key, latest=False).all())

    def get_all_paper_numbers_using_a_rubric(self, rubric_key: str) -> list[int]:
        """Get a list of paper number using the given rubric.

        Args:
            rubric_key: the identifier of the rubric.

        Returns:
            A list of paper number using that rubric.
        """
        seen_paper = set()
        paper_numbers = list()
        # Iterate from newest to oldest updates, ignore duplicate papers seen at later time
        # Append to paper_numbers if the *NEWEST* annotation on that paper uses the rubric.
        annotions_using_the_rubric = Rubric.objects.get(
            key=rubric_key
        ).annotations.all()

        annotations = Annotation.objects.all().order_by("-time_of_last_update")
        for annotation in annotations:
            paper_number = annotation.task.paper.paper_number
            if (paper_number not in seen_paper) and (
                annotation in annotions_using_the_rubric
            ):
                paper_numbers.append(paper_number)
            seen_paper.add(paper_number)

        return paper_numbers

    def get_rubric_by_key_as_dict(self, rubric_key: str) -> dict[str, Any]:
        """Get a rubric by its key/id and return as a dictionary.

        Args:
            rubric_key: which rubric.  Note currently the key/id is not
                the same as the internal ``pk``.

        Returns:
            Key-value pairs representing the rubric.
        """
        r = Rubric.objects.get(key=rubric_key, latest=True)
        return _Rubric_to_dict(r)

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
        self._build_system_rubrics(username)
        return True

    def _build_system_rubrics(self, username: str) -> None:
        log.info("Building special manager-generated rubrics")
        # create standard manager delta-rubrics - but no 0, nor +/- max-mark
        for q in SpecificationService.get_question_indices():
            mx = SpecificationService.get_question_max_mark(q)
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
                "system_rubric": True,
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
                "system_rubric": True,
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
                "system_rubric": True,
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
                    "system_rubric": True,
                }
                r = self.create_rubric(rubric)
                log.info("Built delta-rubric +%d for Q%s: %s", m, q, r["id"])
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
                    "system_rubric": True,
                }
                r = self.create_rubric(rubric)
                log.info("Built delta-rubric -%d for Q%s: %s", m, q, r["id"])

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
            question: which question index.

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
            question: question index associated with the rubric pane.
            data: dict representing the new pane
        """
        pane = RubricPane.objects.get(user=user, question=question)
        pane.data = data
        pane.save()

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

    def get_rubric_as_html(self, rubric: Rubric) -> str:
        """Gets a rubric as HTML.

        Args:
            rubric: a Rubric instance

        Returns:
            HTML representation of the rubric.

        TODO: code duplication from plom.client.rubrics.py.
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
