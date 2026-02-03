# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2023 Brennen Chiu
# Copyright (C) 2019-2026 Colin B. Macdonald
# Copyright (C) 2019-2025 Andrew Rechnitzer
# Copyright (C) 2020 Dryden Wiebe
# Copyright (C) 2021 Nicholas J H Lai
# Copyright (C) 2023 Julian Lapenna
# Copyright (C) 2023 Divy Patel
# Copyright (C) 2023 Natalie Balashov
# Copyright (C) 2024-2025 Aden Chan
# Copyright (C) 2024-2025 Bryan Tanady
# Copyright (C) 2024-2025 Aidan Murphy
# Copyright (C) 2025 Deep Shah

import ast
import csv
import io
import html
import json
import logging
import sys
from operator import itemgetter
from typing import Any

if sys.version_info < (3, 11):
    import tomli as tomllib
else:
    import tomllib
import tomlkit

from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
from django.db import transaction
from django.db.models.aggregates import Count
from django.db.models import QuerySet
from rest_framework import serializers

from plom.plom_exceptions import PlomConflict
from plom_server.Base.services import Settings
from plom_server.Mark.models import Annotation
from plom_server.Mark.models.tasks import MarkingTask
from plom_server.Papers.models import Paper
from plom_server.Papers.services import SpecificationService
from plom_server.QuestionTags.models import PedagogyTag
from ..serializers import RubricSerializer
from ..models import Rubric
from ..models import RubricPane
from .rubric_permissions import RubricPermissionsService
from .utils import _generate_display_delta, _Rubric_to_dict


log = logging.getLogger("RubricService")


# TODO: validation of JSONFields that the model/form/serializer could/should
# be doing (see `clean_versions` commented out in Rubrics/models.py)
# These `_validate_...` functions are written something like `clean_<field>`
# in Django's model/form.


def _validate_versions_in_range(vers: None | str) -> None:
    if not vers:
        return

    # The serialzer is going to do all this, except for the range check,
    # but b/c the seralizer hasn't run yet, we need to parse.  We could
    # consider moving this check to the serializer but its does require
    # looking up the number of versions in another table...

    if not isinstance(vers, str):
        raise serializers.ValidationError({"versions": "Input must be string"})
    try:
        parsed_vers = [int(x.strip()) for x in vers.split(",")]
    except ValueError as e:
        _errmsg = f'nonempty "versions" must be a comma-separated list of ints but got "{vers}": {e}'
        raise serializers.ValidationError({"versions": _errmsg})

    n_versions = SpecificationService.get_n_versions()
    for v in parsed_vers:
        if v < 1 or v > n_versions:
            _errmsg = f"Version {v} is out of range — must be in [1, {n_versions}]"
            raise serializers.ValidationError({"versions": _errmsg})


def _validate_parameters(parameters: None | list, num_versions: None | int = 1) -> None:
    if not parameters:
        return

    if not isinstance(parameters, list):
        raise serializers.ValidationError(
            'nonempty "parameters" must be a list but got'
            f' type {type(parameters)}: "{parameters}"'
        )
    for row in parameters:
        try:
            param, values = row
        except ValueError as e:
            raise serializers.ValidationError(
                f'Invalid row in "parameters": {e}'
            ) from e

        if not isinstance(param, str):
            raise serializers.ValidationError(
                'Invalid row in "parameters": first row entry "param" should be str'
                f' but has type "{type(param)}"; row: "{row}"'
            )

        if not (isinstance(values, tuple) or isinstance(values, list)):
            raise serializers.ValidationError(
                'Invalid row in "parameters": expected list of substitution values;'
                f' got type "{type(values)}"; row: "{row}"'
            )

        if not len(values) == num_versions:
            raise serializers.ValidationError(
                f'Invalid row in "parameters": must provide {num_versions}'
                f' substitutions, only {len(values)} provided; row: "{row}"'
            )

        for v in values:
            if not isinstance(v, str):
                raise serializers.ValidationError(
                    'Invalid row in "parameters": expected list of str substitutions;'
                    f' value "{v}" has "{type(v)}"; row: "{row}"'
                )


# TODO: this code belongs in model/serializer?
def _validate_value(value: int | float | str, max_mark: int) -> None:
    # check that the "value" lies in [-max_mark, max_mark]
    try:
        value = float(value)
    except ValueError as e:
        raise serializers.ValidationError(
            {"value": f"value {value} must be convertible to number: {e}"}
        ) from e
    if not -max_mark <= value <= max_mark:
        raise serializers.ValidationError(
            {"value": f"Value out of range: must lie in [-{max_mark}, {max_mark}]"}
        )


def _validate_value_out_of(value, out_of, max_mark: int) -> None:
    try:
        out_of = float(out_of)
    except (ValueError, TypeError) as e:
        raise serializers.ValidationError(
            {"out_of": f"out of {out_of} must be convertible to number: {e}"}
        ) from e
    try:
        value = float(value)
    except (ValueError, TypeError) as e:
        raise serializers.ValidationError(
            {"value": f"value {value} must be convertible to number: {e}"}
        ) from e
    if not 0 <= value <= out_of:
        raise serializers.ValidationError(
            {"value": f"out of range: {value} is not in [0, {out_of}]."}
        )
    if not 0 < out_of <= max_mark:
        raise serializers.ValidationError(
            {"out_of": f"out of range: {out_of} is not in (0, {max_mark}]"}
        )


# TODO: consider refactoring to wherever we compute diffs
def _is_rubric_change_considered_minor(
    old: Rubric, new_data: dict[str, Any]
) -> tuple[bool, str]:
    """Implements a reject list of non-minor changes.

    Args:
        old: a Rubric object.
        new_data: dict data for the proposed new rubric.

    Returns:
        Tuple of True/False and a string displaying the reason.  Reason
        will be empty when the boolean is True.
    """
    if new_data["rid"] != old.rid:
        return (False, "Changed rid")
    if new_data["revision"] != old.revision:
        return (False, "Changed revision")
    if new_data["kind"] != old.kind:
        return (False, "Changed kind")
    if new_data["kind"] != "neutral":
        # neutral rubrics might not have "value"
        if new_data["value"] != old.value:
            return (False, "Changed value")
    if new_data["kind"] == "absolute":
        # non-absolute rubrics might not have "out_of"
        if new_data["out_of"] != old.out_of:
            return (False, "Changed out_of")
    if new_data["question_index"] != old.question_index:
        return (False, "Changed question_index")

    # text is a grey area!  For now, leave minor: users can force a major change
    # TODO: or maybe we could refuse to decide and FORCE user to make a choice

    return (True, "")


def _modify_rubric_in_place(old: Rubric, serializer: RubricSerializer) -> Rubric:
    log.info(
        f"Modifying rubric {old.rid} rev {old.revision}.{old.subrevision} in-place"
    )
    serializer.validated_data["latest"] = True
    serializer.validated_data["subrevision"] += 1
    return serializer.update(old, serializer.validated_data)


def _modify_rubric_by_making_new_one(
    old: Rubric, serializer: RubricSerializer
) -> Rubric:
    log.info(
        f"Modifying rubric {old.rid} rev {old.revision}.{old.subrevision} by"
        " making a new rubric with bumped revision"
    )
    # if the old rubric was a system rubric, we should not allow that to change
    if old.system_rubric:
        serializer.validated_data["system_rubric"] = True
    old.latest = False
    old.save()
    serializer.validated_data["revision"] += 1
    serializer.validated_data["subrevision"] = 0
    serializer.validated_data["latest"] = True
    return serializer.save()


class RubricService:
    """Class to encapsulate functions for creating and modifying rubrics."""

    _sentinel_no_input = object()

    @classmethod
    def create_rubric(
        cls,
        rubric_data: dict[str, Any],
        *,
        creating_user: User | None | object = _sentinel_no_input,
        by_system: bool = True,
    ) -> dict[str, Any]:
        """Create a rubric using data submitted by a marker.

        Args:
            rubric_data: data for a rubric submitted by a web request.
                This input will not be modified by this call.

        Keyword Args:
            creating_user: who is trying to create the rubric.
                If you omit this kwarg, it will be auto-detected from the
                "username" field of the rubric data.
                The special value of ``None`` means you don't care who
                (probably for internal use only).  ``None`` also bypasses
                the rubric access settings, which is dangerous so is not
                the default: you must specify it explicitly (e.g., Issue #4147).
            by_system: true if the rubric creation is made by system.

        Returns:
            The new rubric data, in dict key-value format.

        Raises:
            KeyError: if rubric_data contains missing username or user.
            serializers.ValidationError: if rubric kind is not a valid
                option, or other errors.
            ValueError: if username does not exist in the DB.  Some validation
                errors might end up here too, such as when fractional rubrics
                are disallowed.
            PermissionDenied: user are not allowed to create rubrics.
                This could be "this user" or "all users".
        """
        if creating_user == cls._sentinel_no_input:
            print("no creating_user specified, taking from data...")
            username = rubric_data.get("username")
            if not username:
                raise KeyError(
                    '"creating_user" not specified and data has no "username" field'
                )
            try:
                creating_user = User.objects.get(username=username)
            except User.DoesNotExist as e:
                raise ValueError(f'User "{username}" does not exist: {e}') from e
            print(f"no creating_user specified, using '{creating_user}' from data")
        rubric_obj = cls._create_rubric(
            rubric_data, creating_user=creating_user, by_system=by_system
        )
        return _Rubric_to_dict(rubric_obj)

    # implementation detail of the above, independently testable
    @classmethod
    def _create_rubric(
        cls,
        incoming_data: dict[str, Any],
        *,
        creating_user: User | None = None,
        by_system: bool = True,
    ) -> Rubric:
        incoming_data = incoming_data.copy()

        if not by_system:
            if not creating_user:
                raise ValueError("Uploader of rubrics is unknown")
            incoming_data["user"] = creating_user.pk
            incoming_data["modified_by_user"] = creating_user.pk

        else:
            # some mangling around user/username here
            if "user" not in incoming_data.keys():
                username = incoming_data.pop("username", None)
                if not username:
                    # TODO: revisit this in the context of uploading rubrics from files
                    raise KeyError(
                        "user or username is required (for now, might change in future)"
                    )
                try:
                    user = User.objects.get(username=username)
                    incoming_data["user"] = user.pk
                    incoming_data["modified_by_user"] = user.pk
                except ObjectDoesNotExist as e:
                    raise ValueError(f"User {username} does not exist.") from e

        if "rid" in incoming_data.keys():
            # could potentially allow blank rid...
            raise serializers.ValidationError(
                'Data for creating a new rubric must not have a "rid" column,'
                f' but this has {incoming_data.get("rid")}'
            )

        # some mangling because client still uses "question"
        # checking if question_index/question column is present
        if "question_index" not in incoming_data:
            if "question" in incoming_data:
                incoming_data["question_index"] = incoming_data.pop("question")
            else:
                raise serializers.ValidationError(
                    {"question_index": "question index is required."}
                )

        if "kind" not in incoming_data.keys():
            raise serializers.ValidationError({"kind": "Kind is required."})

        if incoming_data["kind"] not in ("absolute", "relative", "neutral"):
            raise serializers.ValidationError(
                {"kind": f"{incoming_data['kind']} is not a valid kind."}
            )

        # Check permissions
        who_can_create_rubrics = Settings.get_who_can_create_rubrics()
        if creating_user is None:
            pass
        elif who_can_create_rubrics == "permissive":
            pass
        elif who_can_create_rubrics == "locked":
            raise PermissionDenied(
                "No users are allowed to create rubrics on this server"
            )
        else:
            # neither permissive nor locked so consult per-user permissions
            if creating_user.groups.filter(
                name__in=("lead_marker", "manager")
            ).exists():
                # lead markers / managers can modify any non-system-rubric
                pass
            else:
                raise PermissionDenied(
                    f'You ("{creating_user}") are not allowed to create'
                    " rubrics on this server"
                )
            pass

        return cls._create_rubric_lowlevel(incoming_data)

    @staticmethod
    def _validate_rubric_fields(data: dict[str, Any]) -> None:
        """Validate data that will be used to create rubric.

        Args:
            data: a dictionary representing a rubric.
        """
        # Ensure text is not empty or whitespace only
        if str(data["text"]).strip() == "":
            raise serializers.ValidationError(
                {"text": "Text can't be empty or contain only whitespace"}
            )

        q_index = int(data["question_index"])

        # Ensure question index (indexed from 1) is within range
        max_q_index = SpecificationService.get_n_questions()
        if q_index < 1 or q_index > max_q_index:
            raise serializers.ValidationError(
                {
                    "question_index": f"{q_index} out of range, must be within [1, {max_q_index}]"
                }
            )

        # check that the "value" lies in [-max_mark, max_mark]
        max_mark = SpecificationService.get_question_max_mark(q_index)
        _validate_value(data.get("value", 0), max_mark)

        # TODO: Perhaps the serializer should do this
        if data["kind"] == "absolute":
            if "value" not in data:
                raise serializers.ValidationError(
                    {"value": "Absolute rubric requires value"}
                )
            _validate_value_out_of(data["value"], data["out_of"], max_mark)

        # TODO: more validation of fields that the model/form/serializer could/should
        # be doing (see `clean_versions` commented out in Rubrics/models.py)
        _validate_versions_in_range(data.get("versions"))
        _validate_parameters(
            data.get("parameters"), SpecificationService.get_n_versions()
        )

    @staticmethod
    def _create_rubric_lowlevel(
        data: dict[str, Any],
        *,
        _bypass_serializer: bool = False,
        _bypass_user: User | None = None,
    ) -> Rubric:
        """Create rubrics with less error checking, internal use only.

        Careful with ``_pypass_serializer``.  I think this stuff was introduced
        to decrease the number of database queries when making many rubrics.
        """
        # As stated in Rubric's model: out_of must be 0 for non-absolute kind and value is 0 for neutral
        if data["kind"] != "absolute":
            data["out_of"] = 0
            data["value"] = 0 if data["kind"] == "neutral" else data["value"]

        RubricService._validate_rubric_fields(data)

        if data.get("display_delta", None) is None:
            # if we don't have a display_delta, we'll generate a default one
            data["display_delta"] = _generate_display_delta(
                # if value is missing, can only be neutral
                # missing value will be prohibited in a future MR
                data.get("value", 0),
                data["kind"],
                data.get("out_of", None),
            )
        if data.get("value", None) is not None:
            # do this only if value is present
            data["value"] = RubricPermissionsService.pin_to_allowed_fraction(
                data["value"]
            )

        data["latest"] = True
        if _bypass_serializer:
            assert _bypass_user is not None
            new_rubric = Rubric.objects.create(
                text=data["text"],
                question_index=data["question_index"],
                system_rubric=data["system_rubric"],
                kind=data["kind"],
                value=data["value"],
                out_of=data["out_of"],
                display_delta=data["display_delta"],
                meta=data.get("meta"),
                user=_bypass_user,
                modified_by_user=_bypass_user,
                latest=data.get("latest"),
                versions=data.get("versions", ""),
            )
            for tag in data.get("pedagogy_tags", []):
                new_rubric.pedagogy_tags.add(tag)
            return new_rubric

        serializer = RubricSerializer(data=data)
        # user-friendly text error messages
        if not serializer.is_valid():
            errors = serializer.errors
            friendly = {
                field: "; ".join(err) if isinstance(err, list) else err
                for field, err in errors.items()
            }
            raise serializers.ValidationError(friendly)

        new_rubric = serializer.save()
        # TODO: if its new why do we need to clear these?
        # new_rubric.pedagogy_tags.clear()
        for tag in data.get("pedagogy_tags", []):
            new_rubric.pedagogy_tags.add(tag)
        rubric_obj = serializer.instance
        return rubric_obj

    @classmethod
    @transaction.atomic
    def modify_rubric(
        cls,
        rid: int,
        new_data: dict[str, Any],
        *,
        modifying_user: User | None = None,
        tag_tasks: bool = False,
        is_minor_change: bool | None = None,
    ) -> dict[str, Any]:
        """Modify a rubric.

        Args:
            rid: uniquely identify a rubric, but not a particular revision.
                Generally not the same as the "primary key" used
                internally.
            new_data: data for a rubric submitted by a web request.
                This input will not be modified by this call.

        Keyword Args:
            modifying_user: who is trying to modify the rubric.  This might
                differ from the "owner" of the rubric, i.e., the ``username``
                field inside the ``rubric_data``.  If you pass None (default)
                no checking will be done (probably for internal use).
            tag_tasks: whether to tag all tasks whose latest annotation uses
                this rubric with ``"rubric_changed"``.
                Currently this only works for major changes, or more precisely
                its not yet well-defined what happens if you ask to tag tasks
                for minor changes.
            is_minor_change: by default (passing None) the code will decide
                itself whether this is a minor change.  Callers can force
                one way or the other by passing True or False.
                A minor change is one where you would NOT expect to update
                any existing Annotations that use the Rubric.  For example,
                changing the score is probably NOT a minor change.  Changing
                the text to fix a minor typo might or might not be a minor
                change.  Changing the text drastically should be a major
                change.  Internally, a minor change is one that does not
                bump the revision (and does not create a new rubric) but
                instead modifies the rubric "in-place".

        Returns:
            The modified rubric data, in dict key-value format.

        Exceptions:
            ValueError: wrong "kind" or invalid rubric data.
            PermissionDenied: user does not have permission to modify.
                This could be "this user" or "all users".
            serializers.ValidationError: invalid kind, maybe other invalidity.
            PlomConflict: the new data is too old; someone else modified.
        """
        # addresses a circular import?
        from plom_server.Mark.services import MarkingTaskService

        data = new_data.copy()
        username = data.pop("username")

        try:
            user = User.objects.get(username=username)
        except ObjectDoesNotExist as e:
            raise ValueError(f"User {username} does not exist.") from e

        try:
            old_rubric = (
                Rubric.objects.filter(rid=rid, latest=True).select_for_update().get()
            )
        except Rubric.DoesNotExist as e:
            raise ValueError(f"Rubric {rid} does not exist.") from e

        # default revision if missing from incoming data
        data.setdefault("revision", 0)
        data.setdefault("subrevision", 0)

        # Mid-air collision detection
        if not (
            data["revision"] == old_rubric.revision
            and data["subrevision"] == old_rubric.subrevision
        ):
            # TODO: record who last modified and when
            raise PlomConflict(
                "Your rubric is a change based on revision "
                f'{data["revision"]}.{data["subrevision"]};'
                " this does not match database content "
                f"(revision {old_rubric.revision}.{old_rubric.subrevision}): "
                f"most likely your edits have collided with those of someone else."
            )

        # some mangling because client still uses "question"
        if "question_index" not in data.keys():
            data["question_index"] = data.pop("question")

        who_can_modify_rubrics = Settings.get_who_can_modify_rubrics()
        if modifying_user is None:
            # Generally, omitting modifying_user bypasses checks (for internal use)
            pass
        elif who_can_modify_rubrics == "locked":
            raise PermissionDenied(
                "No users are allowed to modify rubrics on this server"
            )
        elif (
            old_rubric.system_rubric
            and not modifying_user.groups.filter(name="manager").exists()
        ):
            raise PermissionDenied(
                f'Only "manager" users can modify system rubrics (not "{modifying_user}")'
            )
        elif who_can_modify_rubrics == "permissive":
            pass
        else:
            # neither permissive nor locked so consult per-user permissions
            if user == modifying_user:
                # users can modify their own
                pass
            elif modifying_user.groups.filter(name="lead_marker").exists():
                # lead markers can modify any non-system-rubric
                pass
            else:
                raise PermissionDenied(
                    f'You ("{modifying_user}") are not allowed to modify'
                    f' rubrics created by other users (here "{user}")'
                )

        data.pop("modified_by_username", None)

        if modifying_user is not None:
            data["modified_by_user"] = modifying_user.pk

        # To be changed by future MR  (TODO: what does this comment mean?)
        data["user"] = old_rubric.user.pk

        data["rid"] = old_rubric.rid

        if data["kind"] in ("relative", "neutral"):
            data["out_of"] = 0

        # TODO: Perhaps the serializer should do this
        max_mark = SpecificationService.get_question_max_mark(data["question_index"])
        _validate_value(data.get("value", 0), max_mark)

        if data.get("display_delta", None) is None:
            # if we don't have a display_delta, we'll generate a default one
            # This might involve a tolerance (in the case of fractions); if
            # so, we'll adjust the value below using that same tolerance
            data["display_delta"] = _generate_display_delta(
                data.get("value", 0),
                data["kind"],
                data.get("out_of", None),
            )
        if data.get("value", None) is not None:
            # do this only if value is present
            data["value"] = RubricPermissionsService.pin_to_allowed_fraction(
                data["value"]
            )

        if data["kind"] == "absolute":
            _validate_value_out_of(data["value"], data["out_of"], max_mark)

        _validate_versions_in_range(data.get("versions"))

        _validate_parameters(
            data.get("parameters"), SpecificationService.get_n_versions()
        )

        serializer = RubricSerializer(data=data)

        if not serializer.is_valid():
            raise serializers.ValidationError(serializer.errors)

        # autodetect based on a reject list of major change fields
        if is_minor_change is None:
            is_minor_change, reason = _is_rubric_change_considered_minor(
                old_rubric, serializer.validated_data
            )
            if not is_minor_change:
                log.info("autodetected rubric major change: %s", reason)

        if is_minor_change:
            new_rubric = _modify_rubric_in_place(old_rubric, serializer)
        else:
            new_rubric = _modify_rubric_by_making_new_one(old_rubric, serializer)

        if isinstance(data.get("pedagogy_tags"), list):
            data["pedagogy_tags"] = PedagogyTag.objects.filter(
                tag_name__in=data["pedagogy_tags"]
            ).values_list("pk", flat=True)
        new_rubric.pedagogy_tags.set(data.get("pedagogy_tags", []))

        if not is_minor_change and tag_tasks:
            # TODO: or do we need some "system tags" that definitely already exist?
            any_manager = User.objects.filter(groups__name="manager").first()
            tag = MarkingTaskService().get_or_create_tag(any_manager, "rubric_changed")
            # find all complete annotations using older revisions of this rubric
            tasks = MarkingTask.objects.filter(
                status=MarkingTask.COMPLETE,
                latest_annotation__rubric__rid=new_rubric.rid,
                latest_annotation__rubric__revision__lt=new_rubric.revision,
            )
            # A loop over what is hopefully not TOO many tasks...
            # TODO: perhaps Andrew knows how to write an efficient bulk-tagger?
            for task in tasks:
                MarkingTaskService()._add_tag(tag, task)

        return _Rubric_to_dict(new_rubric)

    @classmethod
    def get_rubrics_as_dicts(
        cls,
        *,
        question_idx: int | None = None,
    ) -> list[dict[str, Any]]:
        """Get the rubrics, possibly filtered by question.

        Keyword Args:
            question_idx: question index or ``None`` for all.

        Returns:
            Collection of dictionaries, one for each rubric.
        """
        rubric_queryset = cls.get_all_rubrics()
        if question_idx is not None:
            rubric_queryset = rubric_queryset.filter(
                question_index=question_idx, latest=True
            )
        rubric_data = []

        # see issue #3683 - need to prefetch these fields for
        # the _Rubric_to_dict function.
        # similarly we need to pedagogy tags prefetch
        for r in rubric_queryset.prefetch_related(
            "user", "modified_by_user", "pedagogy_tags"
        ):
            rubric_data.append(_Rubric_to_dict(r))

        new_rubric_data = sorted(rubric_data, key=itemgetter("kind"))
        return new_rubric_data

    @staticmethod
    def get_all_rubrics() -> QuerySet[Rubric]:
        """Get all the rubrics (latest revisions) as a QuerySet, enabling further lazy filtering.

        See: https://docs.djangoproject.com/en/4.2/topics/db/queries/#querysets-are-lazy

        Returns:
            Lazy queryset of all rubrics.
        """
        return Rubric.objects.filter(latest=True)

    def get_all_rubrics_with_counts(self) -> QuerySet[Rubric]:
        """Get all latest rubrics but also annotate with how many times it has been used.

            Times used included all annotations, not just latest ones.
            @arechnitzer promises to fix this behavior in a future MR.

        Returns:
            Lazy queryset of all rubrics with counts.
        """
        qs = self.get_all_rubrics()
        return qs.annotate(times_used=Count("annotations"))

    # TODO: create method to get all rubrics with counts of how many times
    #       it has been used in the latest edition of a paper

    def get_rubric_count(self) -> int:
        """How many rubrics in total (excluding revisions)."""
        return Rubric.objects.filter(latest=True).count()

    @staticmethod
    def get_rubric_by_rid(rid: int) -> Rubric:
        """Get the latest rurbic revision by its rubric id.

        Args:
            rid: which rubric.  Note currently the rid is not
                the same as the internal ``pk`` ("primary key").

        Returns:
            The rubric object.  It is not "selected for update" so should
            be read-only.
        """
        return Rubric.objects.get(rid=rid, latest=True)

    @staticmethod
    def get_past_revisions_by_rid(rid: int) -> list[Rubric]:
        """Get all earlier available revisions of a rubric by the rid, not including the latest one.

        Args:
            rid: which rubric series to we want the past revisions of.

        Returns:
            A list of rubrics with the specified rubric id.
        """
        return list(
            Rubric.objects.filter(rid=rid, latest=False).all().order_by("revision")
        )

    @classmethod
    def init_rubrics(cls) -> bool:
        """Add special rubrics such as deltas and per-question specific.

        Returns:
            True if initialized or False if it was already initialized.
        """
        if Rubric.objects.exists():
            return False
        cls._build_system_rubrics()
        return True

    @classmethod
    def _build_system_rubrics(cls) -> None:
        log.info("Building special manager-generated rubrics")

        # get the first manager object
        any_manager = User.objects.filter(groups__name="manager").first()
        # raise an exception if there aren't any managers.
        if any_manager is None:
            raise ObjectDoesNotExist("No manager users have been created.")
        # TODO: experimenting with passing in User object instead...
        # any_manager_pk = any_manager.pk

        def create_system_rubric(data):
            # data["user"] = any_manager_pk
            # data["modified_by_user"] = any_manager_pk
            data["system_rubric"] = True
            cls._create_rubric_lowlevel(
                data, _bypass_serializer=True, _bypass_user=any_manager
            )

        # create standard manager delta-rubrics - but no 0, nor +/- max-mark
        for q in SpecificationService.get_question_indices():
            mx = SpecificationService.get_question_max_mark(q)
            # make zero mark and full mark rubrics
            rubric = {
                "kind": "absolute",
                "value": 0,
                "out_of": mx,
                "text": "no answer given",
                "question_index": q,
                "meta": "Is this answer blank or nearly blank?  Please do not use "
                + "if there is any possibility of relevant writing on the page.",
                "tags": "",
                "versions": "",
            }
            create_system_rubric(rubric)
            # log.info("Built no-answer-rubric Q%s: key %s", q, r.pk)

            rubric = {
                "kind": "absolute",
                "value": 0,
                "out_of": mx,
                "text": "no marks",
                "question_index": q,
                "meta": "There is writing here but its not sufficient for any points.",
                "tags": "",
                "versions": "",
            }
            create_system_rubric(rubric)
            # log.info("Built no-marks-rubric Q%s: key %s", q, r.pk)

            rubric = {
                "kind": "absolute",
                "value": mx,
                "out_of": mx,
                "text": "full marks",
                "question_index": q,
                "tags": "",
                "versions": "",
            }
            create_system_rubric(rubric)
            # log.info("Built full-marks-rubric Q%s: key %s", q, r.pk)

            # now make +/- delta-rubrics
            for m in range(1, int(mx) + 1):
                rubric = {
                    "value": m,
                    "out_of": 0,
                    "text": ".",
                    "kind": "relative",
                    "question_index": q,
                    "tags": "",
                }
                create_system_rubric(rubric)
                # log.info("Built delta-rubric +%d for Q%s: %s", m, q, r["rid"])
                rubric = {
                    "value": -m,
                    "out_of": 0,
                    "text": ".",
                    "kind": "relative",
                    "question_index": q,
                    "tags": "",
                }
                create_system_rubric(rubric)
                # log.info("Built delta-rubric -%d for Q%s: %s", m, q, r["rid"])

            # TODO: testing non-integer rubrics in demo: change to True
            if False:
                for rubric in [
                    {
                        "display_delta": "+1\N{VULGAR FRACTION ONE HALF}",
                        "value": 1.5,
                        "text": "testing non-integer rubric",
                        "kind": "relative",
                        "question_index": q,
                    },
                    {
                        "value": -0.5,
                        "text": "testing negative non-integer rubric",
                        "kind": "relative",
                        "question_index": q,
                    },
                    {
                        "display_delta": "+a tenth",
                        "value": 1 / 10,
                        "text": "one tenth of one point",
                        "kind": "relative",
                        "question_index": q,
                    },
                    {
                        "display_delta": "+1/29",
                        "value": 1 / 29,
                        "text": "ADR will love co-prime pairs",
                        "kind": "relative",
                        "question_index": q,
                    },
                    {
                        "display_delta": "+1/31",
                        "value": 1 / 31,
                        "text": r"tex: Note that $31 \times 29 = 899$.",
                        "kind": "relative",
                        "question_index": q,
                    },
                    {
                        "display_delta": "1/49 of 1/7",
                        "value": 1 / 49,
                        "out_of": 1 / 7,
                        "text": "testing absolute rubric",
                        "kind": "absolute",
                        "question_index": q,
                    },
                ]:
                    create_system_rubric(rubric)
                    # log.info(
                    #     "Built %s rubric %s for Q%s: %s",
                    #     r["kind"],
                    #     r["display_delta"],
                    #     q,
                    #     r["rid"],
                    # )

    @classmethod
    def build_half_mark_delta_rubrics(cls, username: str) -> None:
        """Create the plus and minus one-half delta rubrics that are optional.

        Args:
            username: which user to associate with the demo rubrics.

        Exceptions:
            ValueError: username does not exist or is not part of the
                manager group, or the half-point rubrics are disabled,
                or these rubrics already exist.
        """
        try:
            user = User.objects.get(username__iexact=username, groups__name="manager")
        except ObjectDoesNotExist as e:
            raise ValueError(
                f"User '{username}' does not exist or has wrong permissions"
            ) from e
        if Rubric.objects.filter(value__exact=0.5).filter(text__exact=".").exists():
            raise ValueError(
                "Could not create half-mark delta rubrics b/c they already exist"
            )
        cls._build_half_mark_delta_rubrics(user)

    @classmethod
    def _build_half_mark_delta_rubrics(cls, user: User) -> None:
        log.info("Building half-mark delta rubrics")
        for q in SpecificationService.get_question_indices():
            rubric = {
                "display_delta": "+\N{VULGAR FRACTION ONE HALF}",
                "value": 0.5,
                "text": ".",
                "kind": "relative",
                "question_index": q,
                "username": user.username,
                "system_rubric": True,
            }
            r = cls.create_rubric(rubric, creating_user=user)
            log.info(
                "Built delta-rubric %s for Qidx %d: %s",
                r["display_delta"],
                r["question_index"],
                r["rid"],
            )

            rubric = {
                "display_delta": "-\N{VULGAR FRACTION ONE HALF}",
                "value": -0.5,
                "text": ".",
                "kind": "relative",
                "question_index": q,
                "username": user.username,
                "system_rubric": True,
            }
            r = cls.create_rubric(rubric, creating_user=user)
            log.info(
                "Built delta-rubric %s for Qidx %d: %s",
                r["display_delta"],
                r["question_index"],
                r["rid"],
            )

    @staticmethod
    def _erase_all_rubrics() -> None:
        """Remove all rubrics, permanently deleting them.  BE CAREFUL.

        Warning - although this checks if any annotations have been produced
        before deleting, it should only be called by the papers_are_printed
        setter, and NO ONE ELSE.

        Raises:
            ValueError: when any annotations have been created.
        """
        if Annotation.objects.exists():
            raise ValueError(
                "Annotations have been created. You cannot delete rubrics."
            )

        Rubric.objects.all().select_for_update().delete()

    @staticmethod
    def get_rubric_pane(user: User, question_idx: int) -> dict[str, Any]:
        """Gets a rubric pane for a user.

        Args:
            user: a User instance
            question_idx: which question by index.

        Returns:
            Rubric pane data as key-value pairs.
        """
        pane, created = RubricPane.objects.get_or_create(
            user=user, question=question_idx
        )
        if created:
            return {}
        return pane.data

    def update_rubric_pane(
        self, user: User, question_idx: int, data: dict[str, Any]
    ) -> None:
        """Updates a rubric pane for a user.

        Args:
            user: a User instance
            question_idx: question index associated with the rubric pane.
            data: dict representing the pane.
        """
        pane = RubricPane.objects.get(user=user, question=question_idx)
        pane.data = data
        pane.save()

    @staticmethod
    def get_annotations_from_rubric(rubric: Rubric) -> QuerySet[Annotation]:
        """Get the QuerySet of Annotations that use this Rubric.

        Args:
            rubric: a Rubric object instance.

        Returns:
            A query set of Annotation instances.
        """
        return rubric.annotations.all()

    @staticmethod
    def get_marking_tasks_with_rubric_in_latest_annotation(
        rubric: Rubric,
    ) -> QuerySet[MarkingTask]:
        """Get the QuerySet of MarkingTasks that use this Rubric in their latest annotations.

        Note: the search is only on the latest annotations but does not
        take revision of the rubric into account: that is you can ask
        with an older revision and you'll still find the match.

        Args:
            rubric: a Rubric object instance.

        Returns:
            A query of MarkingTask instances.
        """
        # Caution here: There is more than one rubric with a particular rid (b/c
        # of rubric revisions).  There should be at most one of those used in the
        # latest annotation but for awhile this was not true (Issue #3647) and we
        # would get get multiple copies of the same task.  Using "distinct" filters
        # out those duplicates:
        # https://docs.djangoproject.com/en/5.1/ref/models/querysets/#distinct
        # TODO: same docs say "if you are using distinct() be careful about ordering
        # by related models": perhaps we should stop ordering this (?)
        # Or rethink this whole query to be less flaky!
        return (
            MarkingTask.objects.filter(
                status=MarkingTask.COMPLETE, latest_annotation__rubric__rid=rubric.rid
            )
            .order_by("paper__paper_number")
            .prefetch_related("paper", "assigned_user", "latest_annotation")
            .distinct()
        )

    @staticmethod
    def get_rubrics_from_annotation(annotation: Annotation) -> QuerySet[Rubric]:
        """Get a QuerySet of Rubrics that are used by a particular Annotation.

        Args:
            annotation: Annotation instance

        Returns:
            Rubric instances
        """
        return Rubric.objects.filter(annotations=annotation)

    @staticmethod
    def get_rubrics_from_paper(paper_obj: Paper) -> QuerySet[Rubric]:
        """Get a QuerySet of Rubrics that are used by a particular Paper.

        Args:
            paper_obj: Paper instance

        Returns:
            Rubric instances
        """
        marking_tasks = MarkingTask.objects.filter(paper=paper_obj)
        annotations = Annotation.objects.filter(task__in=marking_tasks)
        rubrics = Rubric.objects.filter(annotations__in=annotations)
        return rubrics

    @staticmethod
    def get_rubrics_created_by_user(username: str) -> QuerySet[Rubric]:
        """Get the queryset of rubrics created by this user.

        TODO: the interplay b/w created by, owned by, modified by, is a bit
        "up in the air".  Currently this method is unused (although somewhat
        strangely, it is unit-tested).  See discussions in ``models.py``.

        Args:
            username: username of the user

        Returns:
            Rubric instances
        """
        user = User.objects.get(username=username)
        return Rubric.objects.filter(user=user)

    @staticmethod
    def get_rubric_as_html(rubric: Rubric) -> str:
        """Gets a rubric as HTML.

        Args:
            rubric: a Rubric instance

        Returns:
            HTML representation of the rubric.

        TODO: code duplication from plom.rubric_utils.py.
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

    def create_rubric_template(self, question_index: int | None, filetype: str) -> str:
        """Create a template rubric for a particular question in the specified format.

        The template has one absolute rubric entry for each score from 0 to
        out_of (inclusive). It also creates two relative (one positive and negative),
        and one neutral rubric.

        Args:
            question_index: index of the question the rubric template is for, if None,
            all questions will be included.
            filetype: The type of the file (json, toml, csv).

        Returns:
            A string containing the rubric data from the specified file format.
        """
        if question_index:
            rubrics = self._create_rubric_template(question_index=question_index)
        else:
            q_indices = SpecificationService.get_question_indices()
            rubrics = [
                r
                for q in q_indices
                for r in self._create_rubric_template(question_index=q)
            ]

        if filetype == "csv":
            f = io.StringIO()
            writer = csv.DictWriter(f, fieldnames=rubrics[0].keys())
            writer.writeheader()
            writer.writerows(rubrics)
            data_string = f.getvalue()
        elif filetype == "json":
            data_string = json.dumps(rubrics, indent="  ")
        elif filetype == "toml":
            for dictionary in rubrics:
                filtered = {k: v for k, v in dictionary.items() if v is not None}
                dictionary.clear()
                dictionary.update(filtered)
            data_string = tomlkit.dumps({"rubric": rubrics})
        else:
            raise ValueError(f"Unsupported file type: {filetype}")

        return data_string

    def _create_rubric_template(self, question_index: int) -> list[dict[str, Any]]:
        """Create a template rubric in list of dicts format for a particular question.

        Args:
            question_index: index of the question the rubric template is for.

        Returns:
            A list of dict, each represents a rubric.
        """
        template = []

        max_mark = SpecificationService.get_question_max_mark(question_index)

        # Construct absolute rubric
        for value in range(max_mark + 1):
            abs_rubric = self._create_single_rubric_template(
                kind="absolute",
                value=value,
                question_index=question_index,
            )
            template.append(abs_rubric)

        # Construct relative rubric
        relative_rubric_pos = self._create_single_rubric_template(
            kind="relative",
            value=1,
            question_index=question_index,
        )
        relative_rubric_neg = self._create_single_rubric_template(
            kind="relative",
            value=-1,
            question_index=question_index,
        )
        template.extend([relative_rubric_pos, relative_rubric_neg])

        # Construct neutral rubric
        neutral_rubric = self._create_single_rubric_template(
            kind="neutral", value=0, question_index=question_index
        )
        template.append(neutral_rubric)

        return template

    def _create_single_rubric_template(
        self, kind: str, value: int | float | None, question_index: int
    ) -> dict[str, Any]:

        out_of = (
            SpecificationService.get_question_max_mark(question_index)
            if kind == "absolute"
            else None
        )
        value = None if kind == "neutral" else value

        rubric: dict[str, Any] = {
            "kind": kind,
            "value": value,
            "out_of": out_of,
            "text": "==> CHANGE ME",
            "tags": "",
            "meta": "",
            "question_index": question_index,
            "versions": "",
            "parameters": [],
            "pedagogy_tags": [],
        }

        # Validate keys in our hand-rolled dict to those in the official Rubric model
        for key in rubric.keys():
            # Validate key
            if key not in Rubric.__dict__.keys():
                raise ValueError(f"{key} is not a valid Rubric Attribute.")

        return rubric

    def get_rubric_data(self, filetype: str, question_idx: int | None) -> str:
        """Get the rubric data as the string contents of file of a specified type.

        Args:
            filetype: The type of file to generate. Supported file types are "json", "toml", and "csv".
            question_idx: Filter the rubrics by those relevant to this
                question, by index.  If None, all rubrics will be included.

        Returns:
            A string containing the rubric data from the specified file format.

        Raises:
            ValueError: If the specified file type is not supported.
        """
        if filetype == "json":
            if question_idx is not None:
                queryset = Rubric.objects.filter(question_index=question_idx)
            else:
                queryset = Rubric.objects.all()
            serializer = RubricSerializer(queryset, many=True)
            data_string = json.dumps(serializer.data, indent="  ")
        elif filetype == "toml":
            rubrics = self.get_rubrics_as_dicts(question_idx=question_idx)
            for dictionary in rubrics:
                filtered = {k: v for k, v in dictionary.items() if v is not None}
                dictionary.clear()
                dictionary.update(filtered)
            data_string = tomlkit.dumps({"rubric": rubrics})
        elif filetype == "csv":
            rubrics = self.get_rubrics_as_dicts(question_idx=question_idx)
            f = io.StringIO()
            writer = csv.DictWriter(f, fieldnames=rubrics[0].keys())
            writer.writeheader()
            writer.writerows(rubrics)
            data_string = f.getvalue()
        else:
            raise ValueError(f"Unsupported file type: {filetype}")

        return data_string

    @classmethod
    def create_rubrics_from_file_data(
        cls,
        data: str,
        filetype: str,
        by_system: bool,
        requesting_user: str | None = None,
    ) -> list[dict[str, Any]]:
        """Retrieves rubric data from a file and create rubric for each.

        Args:
            data: The file object containing the rubrics.
            filetype: The type of the file (json, toml, csv).
            by_system: true if the update is called by system and requesting_user is irrelevant.
            requesting_user: the user who requested to update the rubric data.
            ``None`` means you don't care who (probably for internal use only).

        Returns:
            A list of the rubrics created.

        Raises:
            ValueError: If the file type is not supported.  Also if
                username does not exist.
            PermissionDenied: username not allowed to make rubrics.
            serializers.ValidationError: rubric data is invalid.
            KeyError: TODO, what should happen if no user specified?
                See also TODO in the create code.
        """
        if filetype == "json":
            rubrics = json.loads(data)
        elif filetype == "toml":
            rubrics = tomllib.loads(data)["rubric"]
        elif filetype == "csv":
            f = io.StringIO(data)
            reader = csv.DictReader(f)
            rubrics = list(reader)
        else:
            raise ValueError(f"Unsupported file type: {filetype}")

        # This smells like ask-permission: try to avoid too much "pre-validation"
        # and instead leave that for the rubric creation code.  Try to keep this
        # code specific to file uploads, e.g., csv ambiguities.
        for r in rubrics:
            # Fixes for Issue #3807: csv often scramble empty lists or otherwise makes strings
            if r.get("pedagogy_tags") == "[]":
                r["pedagogy_tags"] = []

            if r.get("parameters") in ("[]", ""):
                r["parameters"] = []
            if isinstance(r.get("parameters"), str):
                parameters = r["parameters"]
                log.debug('evaluating string "parameters" input')
                try:
                    parameters = ast.literal_eval(parameters)
                except (SyntaxError, ValueError) as e:
                    raise serializers.ValidationError(
                        f'Invalid "parameters" field of type {type(parameters)}: {e}'
                    ) from e
                r["parameters"] = parameters

        if requesting_user:
            user = User.objects.get(username=requesting_user)
        else:
            user = None

        # ensure either all rubrics succeed or all fail
        with transaction.atomic():
            return [
                cls.create_rubric(r, creating_user=user, by_system=by_system)
                for r in rubrics
            ]
