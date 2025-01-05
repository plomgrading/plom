# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2023 Brennen Chiu
# Copyright (C) 2019-2024 Colin B. Macdonald
# Copyright (C) 2019-2024 Andrew Rechnitzer
# Copyright (C) 2020 Dryden Wiebe
# Copyright (C) 2021 Nicholas J H Lai
# Copyright (C) 2023 Julian Lapenna
# Copyright (C) 2023 Divy Patel
# Copyright (C) 2023 Natalie Balashov
# Copyright (C) 2024 Aden Chan
# Copyright (C) 2024 Bryan Tanady
# Copyright (C) 2024 Aidan Murphy

from __future__ import annotations

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
from rest_framework.exceptions import ValidationError

from plom.plom_exceptions import PlomConflict
from Base.models import SettingsModel
from Mark.models import Annotation
from Mark.models.tasks import MarkingTask
from Mark.services import MarkingTaskService
from Papers.models import Paper
from Papers.services import SpecificationService
from ..serializers import RubricSerializer
from ..models import Rubric
from ..models import RubricPane


log = logging.getLogger("RubricServer")


def _Rubric_to_dict(r: Rubric) -> dict[str, Any]:
    return {
        "rid": r.rid,
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
        self, incoming_data: dict[str, Any], *, creating_user: User | None = None
    ) -> Rubric:
        incoming_data = incoming_data.copy()

        # some mangling around user/username here
        if "user" not in incoming_data.keys():
            username = incoming_data.pop("username")
            try:
                user = User.objects.get(username=username)
                incoming_data["user"] = user.pk
                incoming_data["modified_by_user"] = user.pk
            except ObjectDoesNotExist as e:
                raise ValueError(f"User {username} does not exist.") from e

        if "kind" not in incoming_data.keys():
            raise ValidationError({"kind": "Kind is required."})

        if incoming_data["kind"] not in ("absolute", "relative", "neutral"):
            raise ValidationError({"kind": "Invalid kind."})

        # Check permissions
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
            # neither permissive nor locked so consult per-user permissions
            if creating_user.groups.filter(name="lead_marker").exists():
                # lead markers can modify any non-system-rubric
                pass
            else:
                raise PermissionDenied(
                    f'You ("{creating_user}") are not allowed to create'
                    " rubrics on this server"
                )
            pass

        return self._create_rubric_lowlevel(incoming_data)

    # less error checking, for internal use only
    def _create_rubric_lowlevel(
        self,
        data: dict[str, Any],
        *,
        _bypass_serializer: bool = False,
        _bypass_user: User | None = None,
    ) -> Rubric:
        if data.get("display_delta", None) is None:
            # if we don't have a display_delta, we'll generate a default one
            data["display_delta"] = self._generate_display_delta(
                # if value is missing, can only be neutral
                # missing value will be prohibited in a future MR
                data.get("value", 0),
                data["kind"],
                data.get("out_of", None),
            )
        data["latest"] = True
        if _bypass_serializer:
            new_rubric = Rubric.objects.create(
                text=data["text"],
                question=data["question"],
                system_rubric=data["system_rubric"],
                kind=data["kind"],
                value=data["value"],
                out_of=data["out_of"],
                display_delta=data.get("display_delta"),
                meta=data.get("meta"),
                user=_bypass_user,  # TODO: None seems just fine too (?)
                modified_by_user=_bypass_user,
                latest=data.get("latest"),
                versions=data.get("versions"),
            )
            for tag in data.get("pedagogy_tags", []):
                new_rubric.pedagogy_tags.add(tag)
            return new_rubric

        serializer = RubricSerializer(data=data)
        if not serializer.is_valid():
            raise ValidationError(serializer.errors)
        new_rubric = serializer.save()
        # TODO: if its new why do we need to clear these?
        # new_rubric.pedagogy_tags.clear()
        for tag in data.get("pedagogy_tags", []):
            new_rubric.pedagogy_tags.add(tag)
        rubric_obj = serializer.instance
        return rubric_obj

    @transaction.atomic
    def modify_rubric(
        self,
        rid: int,
        new_rubric_data: dict[str, Any],
        *,
        modifying_user: User | None = None,
        tag_tasks: bool = False,
    ) -> dict[str, Any]:
        """Modify a rubric.

        Args:
            rid: uniquely identify a rubric, but not a particular revision.
                Generally not the same as the "primary key" used
                internally.
            new_rubric_data: data for a rubric submitted by a web request.
                This input will not be modified by this call.

        Keyword Args:
            modifying_user: who is trying to modify the rubric.  This might
                differ from the "owner" of the rubric, i.e., the ``username``
                field inside the ``rubric_data``.  If you pass None (default)
                no checking will be done (probably for internal use).
            tag_tasks: whether to tag all tasks whose latest annotation uses
                this rubric with ``"rubric_changed"``.

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
        except ObjectDoesNotExist as e:
            raise ValueError(f"User {username} does not exist.") from e

        try:
            old_rubric = (
                Rubric.objects.filter(rid=rid, latest=True).select_for_update().get()
            )
        except Rubric.DoesNotExist as e:
            raise ValueError(f"Rubric {rid} does not exist.") from e

        # default revision if missing from incoming data
        new_rubric_data.setdefault("revision", 0)

        # incoming revision is not incremented to check if what the
        # revision was based on is outdated
        if not new_rubric_data["revision"] == old_rubric.revision:
            # TODO: record who last modified and when
            raise PlomConflict(
                f'The rubric your revision was based upon {new_rubric_data["revision"]} '
                f"does not match database content (revision {old_rubric.revision}): "
                f"most likely your edits have collided with those of someone else."
            )

        # Generally, omitting modifying_user bypasses checks
        if modifying_user is None:
            pass
        elif old_rubric.system_rubric:
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

        new_rubric_data.pop("modified_by_username", None)

        if modifying_user is not None:
            new_rubric_data["modified_by_user"] = modifying_user.pk

        # To be changed by future MR  (TODO: what does this comment mean?)
        new_rubric_data["user"] = old_rubric.user.pk
        new_rubric_data["revision"] += 1
        new_rubric_data["latest"] = True
        new_rubric_data["rid"] = old_rubric.rid

        # TODO TODO: Issue #3582: don't autogenerate if input has custom display delta
        new_rubric_data["display_delta"] = self._generate_display_delta(
            new_rubric_data.get("value", 0),
            new_rubric_data["kind"],
            new_rubric_data.get("out_of", None),
        )

        if new_rubric_data["kind"] in ("relative", "neutral"):
            new_rubric_data["out_of"] = 0

        serializer = RubricSerializer(data=new_rubric_data)

        if not serializer.is_valid():
            raise ValidationError(serializer.errors)

        old_rubric.latest = False
        old_rubric.save()

        new_rubric = serializer.save()

        new_rubric.pedagogy_tags.clear()
        for tag in new_rubric_data.get("pedagogy_tags", []):
            new_rubric.pedagogy_tags.add(tag)

        if tag_tasks:
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

        rubric_obj = serializer.instance
        return _Rubric_to_dict(rubric_obj)

    def _generate_display_delta(
        self,
        value: int | float | str,
        kind: str,
        out_of: int | float | str | None = None,
    ) -> str:
        """Generate the display delta for a rubric.

        Keyword Args:
            value: the value of the rubric.
            kind: the kind of the rubric.
            out_of: the maximum value of the rubric, required for
                absolute rubrics, none for other rubrics

        Raises:
            ValueError: if the kind is not valid.
            ValueError: if the kind is absolute and out_of is not provided.
        """
        value = float(value) if isinstance(value, str) else value
        out_of = float(out_of) if isinstance(out_of, str) else out_of

        # TODO: we may want to special case vulgar fractions in the future

        if kind == "absolute":
            if out_of is None:
                raise ValueError("out_of is required for absolute rubrics.")
            else:
                if isinstance(value, int) or value.is_integer():
                    return f"{value:g} of {out_of:g}"
                else:
                    return f"{value} of {out_of}"
        elif kind == "relative":
            if value > 0:
                return f"+{value:g}"
            else:
                # Negative sign gets applied automatically
                return f"{value:g}"
        elif kind == "neutral":
            return "."
        else:
            raise ValueError(f"Invalid kind: {kind}.")

    @classmethod
    def get_rubrics_as_dicts(
        cls, *, question: int | None = None
    ) -> list[dict[str, Any]]:
        """Get the rubrics, possibly filtered by question.

        Keyword Args:
            question: question index or ``None`` for all.

        Returns:
            Collection of dictionaries, one for each rubric.
        """
        rubric_queryset = cls.get_all_rubrics()
        if question is not None:
            rubric_queryset = rubric_queryset.filter(question=question, latest=True)
        rubric_data = []

        # see issue #3683 - need to prefetch these fields for
        # the _Rubric_to_dict function.
        for r in rubric_queryset.prefetch_related("user", "modified_by_user"):
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

    def get_rubric_by_rid(self, rid: int) -> Rubric:
        """Get the latest rurbic revision by its rubric id.

        Args:
            rid: which rubric.  Note currently the rid is not
                the same as the internal ``pk`` ("primary key").

        Returns:
            The rubric object.  It is not "selected for update" so should
            be read-only.
        """
        return Rubric.objects.get(rid=rid, latest=True)

    def get_past_revisions_by_rid(self, rid: int) -> list[Rubric]:
        """Get all earlier revisions of a rubric by the rid, not including the latest one.

        Args:
            rid: which rubric series to we want the past revisions of.

        Returns:
            A list of rubrics with the specified rubric id.
        """
        return list(
            Rubric.objects.filter(rid=rid, latest=False).all().order_by("revision")
        )

    def init_rubrics(self) -> bool:
        """Add special rubrics such as deltas and per-question specific.

        Returns:
            True if initialized or False if it was already initialized.
        """
        if Rubric.objects.exists():
            return False
        self._build_system_rubrics()
        return True

    def _build_system_rubrics(self) -> None:
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
            self._create_rubric_lowlevel(
                data, _bypass_serializer=True, _bypass_user=any_manager
            )

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
            }
            create_system_rubric(rubric)
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
            }
            create_system_rubric(rubric)
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
            }
            create_system_rubric(rubric)
            # log.info("Built full-marks-rubric Q%s: key %s", q, r.pk)

            # now make delta-rubrics
            for m in range(1, int(mx) + 1):
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
                }
                create_system_rubric(rubric)
                # log.info("Built delta-rubric +%d for Q%s: %s", m, q, r["rid"])
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
                }
                create_system_rubric(rubric)
                # log.info("Built delta-rubric -%d for Q%s: %s", m, q, r["rid"])

            # TODO: testing non-integer rubrics in demo: change to True
            if False:
                for rubric in [
                    {
                        "display_delta": "+1\N{Vulgar Fraction One Half}",
                        "value": 1.5,
                        "text": "testing non-integer rubric",
                        "kind": "relative",
                        "question": q,
                    },
                    {
                        "display_delta": "-\N{Vulgar Fraction One Half}",
                        "value": -0.5,
                        "text": "testing negative non-integer rubric",
                        "kind": "relative",
                        "question": q,
                    },
                    {
                        "display_delta": "+a tenth",
                        "value": 1 / 10,
                        "text": "one tenth of one point",
                        "kind": "relative",
                        "question": q,
                    },
                    {
                        "display_delta": "+1/29",
                        "value": 1 / 29,
                        "text": "ADR will love co-prime pairs",
                        "kind": "relative",
                        "question": q,
                    },
                    {
                        "display_delta": "+1/31",
                        "value": 1 / 31,
                        "text": r"tex: Note that $31 \times 29 = 899$.",
                        "kind": "relative",
                        "question": q,
                    },
                    {
                        "display_delta": "1/49 of 1/7",
                        "value": 1 / 49,
                        "out_of": 1 / 7,
                        "text": "testing absolute rubric",
                        "kind": "absolute",
                        "question": q,
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

    def build_half_mark_delta_rubrics(self, username: str) -> bool:
        """Create the plus and minus one-half delta rubrics that are optional.

        Args:
            username: which user to associate with the demo rubrics.

        Returns:
            True if initialized or False if already initialized.

        Exceptions:
            ValueError: username does not exist or is not part of the manager group.
        """
        try:
            _ = User.objects.get(username__iexact=username, groups__name="manager")
        except ObjectDoesNotExist as e:
            raise ValueError(
                f"User '{username}' does not exist or has wrong permissions!"
            ) from e
        existing_demo_rubrics = (
            Rubric.objects.all().filter(value__exact=0.5).filter(text__exact=".")
        )
        if existing_demo_rubrics:
            return False
        self._build_half_mark_delta_rubrics(username)
        return True

    def _build_half_mark_delta_rubrics(self, username: str) -> None:
        log.info("Building half-mark delta rubrics")
        for q in SpecificationService.get_question_indices():
            rubric = {
                "display_delta": "+\N{Vulgar Fraction One Half}",
                "value": 0.5,
                "text": ".",
                "kind": "relative",
                "question": q,
                "username": username,
                "system_rubric": True,
            }
            r = self.create_rubric(rubric)
            log.info(
                "Built delta-rubric %s for Qidx %d: %s",
                r["display_delta"],
                r["question"],
                r["rid"],
            )

            rubric = {
                "display_delta": "-\N{Vulgar Fraction One Half}",
                "value": -0.5,
                "text": ".",
                "kind": "relative",
                "question": q,
                "username": username,
                "system_rubric": True,
            }
            r = self.create_rubric(rubric)
            log.info(
                "Built delta-rubric %s for Qidx %d: %s",
                r["display_delta"],
                r["question"],
                r["rid"],
            )

    def _erase_all_rubrics(self) -> None:
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
        """Get the QuerySet of Annotations that use this Rubric.

        Args:
            rubric: a Rubric object instance.

        Returns:
            A query set of Annotation instances.
        """
        return rubric.annotations.all()

    def get_marking_tasks_with_rubric_in_latest_annotation(
        self, rubric: Rubric
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

    def get_rubric_data(self, filetype: str, question: int | None) -> str:
        """Get the rubric data as a file.

        Args:
            filetype: The type of file to generate. Supported file types are "json", "toml", and "csv".
            question: The question ID to filter the rubric data. If None, all rubrics will be included.

        Returns:
            A string containing the rubric data from the specified file format.

        Raises:
            ValueError: If the specified file type is not supported.
        """
        rubrics = self.get_rubrics_as_dicts(question=question)

        if filetype == "json":
            if question is not None:
                queryset = Rubric.objects.filter(question=question)
            else:
                queryset = Rubric.objects.all()
            serializer = RubricSerializer(queryset, many=True)
            data_string = json.dumps(serializer.data, indent="  ")
        elif filetype == "toml":
            for dictionary in rubrics:
                filtered = {k: v for k, v in dictionary.items() if v is not None}
                dictionary.clear()
                dictionary.update(filtered)
            data_string = tomlkit.dumps({"rubric": rubrics})
        elif filetype == "csv":
            f = io.StringIO()
            writer = csv.DictWriter(f, fieldnames=rubrics[0].keys())
            writer.writeheader()
            writer.writerows(rubrics)
            data_string = f.getvalue()
        else:
            raise ValueError(f"Unsupported file type: {filetype}")

        return data_string

    def update_rubric_data(self, data: str, filetype: str) -> list[dict[str, Any]]:
        """Retrieves rubrics from a file.

        Args:
            data: The file object containing the rubrics.
            filetype: The type of the file (json, toml, csv).

        Returns:
            A list of the rubrics created.

        Raises:
            ValueError: If the file type is not supported.
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

        return [self.create_rubric(r) for r in rubrics]
