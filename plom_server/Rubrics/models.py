# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2023 Brennen Chiu
# Copyright (C) 2023-2025 Colin B. Macdonald
# Copyright (C) 2023 Julian Lapenna
# Copyright (C) 2023 Natalie Balashov
# Copyright (C) 2024 Aidan Murphy
# Copyright (C) 2024 Aden Chan

import random

from django.db import models
from django.contrib.auth.models import User
from django.core.validators import (
    MinValueValidator,
    validate_comma_separated_integer_list,
)
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
import django_tables2

# from django.db.models import Max
# from django.db.models.query_utils import Q

from plom_server.Mark.models.annotations import Annotation


def generate_rid():
    # TODO: tricky to avoid a race with this here:
    # count = Rubric.objects.aggregate(Max("rid"))["rid__max"]
    # return 1 if count is None else count + 1

    def _gen_rid():
        # unsigned intmax or something like that
        return random.randint(1, 2_100_000_000)

    # this still has a race condition, just incredibly unlikely to hit it
    rid = _gen_rid()
    existing_rids = Rubric.objects.all().values_list("rid", flat=True)
    while rid in existing_rids:
        rid = _gen_rid()
    return rid


class Rubric(models.Model):
    """Represents a marker's comment and mark delta for a particular question.

    Fields:
        rid: a unique key/id for accessing or uniquely identifying
            a rubric.  It is not generally (and currently isn't) the
            same as the ``pk`` (the "primary key"), which is an internal
            field, and implementation-specific. `generate_rid` is only
            run when creating a new rubric, and is not run when updating an
            existing rubric via the rubric service, ensuring that
            the same rid is preserved across revisions, even if
            we use new rows (new ``pk``) for each revision.
        kind: one of "relative"; "abs"; or "neutral". This field indicates how the
            ``value`` and ``out_of`` fields are to be interpreted.
            "relative" rubrics have a ``value`` indicating a change in score,
            this can be positive or negative; ``out_of`` should be 0.
            "abs"(olute) rubrics hold a flat score assignment
            of {``value``}/{``score``}.
            "neutral" rubrics indicate no change in score,
            ``value`` and ``out_of`` are both 0.
        display_delta: a short string to display, such as "+3" or "2 of 3",
            that illustrates to recipients how their score is changed by
            this rubric; its format is pre-defined by ``kind``.
        value: the internal score change associated with this rubric, not shown
            to recipients. This should generally be somehow related to
            the display delta, although the exact calculation depends on
            ``kind`` and there maybe be hypothetical future circumstances
            such as mastery grading where the ``display_delta`` might
            differ substantially from ``value``.
        out_of: the maximum possible value for this rubric. only
            for absolute rubrics and is 0 for other types
        text: the text of the rubric
        question_index: the question this rubric is associated with.
        meta: text shown only to markers, not to students.
        parameters: a list of parameters for the rubric, used in
            parameterized rubrics.
        annotations: a mapping to Annotation objects.  Its many-to-many
            so that multiple rubrics can link to multiple Annotations.
        versions: a string containing the versions of ``question``
            this rubric is assigned to, a comma-separated list of integers
            such as ``1, 3``.
            An empty string should be interpreted the same as a list of
            all possible values.
            All should be strictly positive and less than the maximum
            number of versions, although this is not enforced at the database
            level.
        system_rubric: this Rubric was created by or is otherwise
            important to the functioning of the Plom system.  Probably
            readonly or at least extreme caution before poking at.
        published: for future use.
        user: generally who created the rubric, although at least in
            principle, users could "gift" a rubric to another user.
            No one is doing that as of mid 2024.
            TODO: consider renaming to ``created_by_user``?
            Currently, once this makes it to the client, its called
            ``username`` and is a string.  This needs to be dealt with
            on the way in and out (perhaps what a "serializer" is for).
        last_modified: when was this rubric last modified.
        modified_by_user: who last modified this rubric.  Currently, once
            this makes it to the client, its called ``modified_by_username``
            and is a string.
        revision: a monontonically-increasing integer used to track major
            edits to the rubric.
            A major modifying to a rubric will increase this by one, and
            corresponds to making a new row in the Rubric table.
            Both revision and subrevision are used for detection of midair
            collisions during rubric edits.
            If you are messing with revisions/subrevisions directly,
            you are probably doing something creative/hacky.
        subrevision: a monontonically-increasing integer, that is reset to zero
            on each (major) edit and is increased by one on each minor edit.
            Minor edits currently happen "in-place" without creating new rows
            of the Rubric table.
        latest: True when this is the latest version of the rubric and
            false otherwise. There will be only one latest rubric per rid.
        tags: a list of meta tags for this rubric, these are currently used
            for organizing rubrics into groups, although the precise format
            is still in-flux.  Caution: this is not a free-form tagging system
            such as in-use in Tasks.  Special tasks about special meaning to
            the Client.  Currently these are::
                `group:(a)`: indicates that this Rubric is in group "(a)".
                `exclusive:(a)`: at most one Rubric in group "(a)" can
                    be placed on the page.
            These tags can appears more than once.
            Other experimental information can eppear here as well, e.g.,
            in 2025-01, the demo tags its Rubrics as "demo".
        pedagogy_tags: an experimental feature, where Rubrics can be associated
            with, e.g., Learning Objectives for the purposes of generating
            reports for students or pedagogical statistics about the assessment.
            See also "Question Tags": as of 2025-01, these are sometimes
            labelled in this way.

    Notes: the modifications to rubrics are handled in the `rubric_service.py`
    mostly by the ``_modify_rubric_in_place`` and
    ``_modify_rubric_by_making_new_one`` functions.  There are also many
    ``_validate*`` functions there which are effectively part of this model.
    """

    class RubricKind(models.TextChoices):
        ABSOLUTE = "absolute", _("Absolute")
        NEUTRAL = "neutral", _("Neutral")
        RELATIVE = "relative", _("Relative")

    rid = models.IntegerField(null=False, default=generate_rid)
    kind = models.TextField(null=False, choices=RubricKind.choices)
    display_delta = models.TextField(null=False, blank=True, default="")  # is short
    value = models.FloatField(null=False, blank=True, default=0)
    out_of = models.FloatField(
        null=False, blank=True, default=0, validators=[MinValueValidator(0.0)]
    )
    text = models.TextField(null=False)  # can be long
    question_index = models.IntegerField(null=False, blank=False)
    tags = models.TextField(null=True, blank=True, default="")  # can be long
    meta = models.TextField(null=True, blank=True, default="")  # can be long
    versions = models.CharField(
        null=False,
        blank=True,
        default="",
        max_length=255,
        validators=[validate_comma_separated_integer_list],
    )
    parameters = models.JSONField(null=True, blank=True, default=list)
    annotations = models.ManyToManyField(Annotation, blank=True)
    system_rubric = models.BooleanField(null=False, blank=True, default=False)
    published = models.BooleanField(null=False, blank=True, default=True)
    # ForeignKey automatically creates a backreference from the User table
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    last_modified = models.DateTimeField(auto_now=True)
    # This ``modified_by_user`` field would also automatically create a backref
    # from User which would clash with the ``user`` field.  Setting ``related_name``
    # to ``+`` prevents the backref creation, to be revisited it we need the backref
    # https://docs.djangoproject.com/en/5.0/ref/models/fields/#django.db.models.ForeignKey.related_name "
    modified_by_user = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    revision = models.IntegerField(null=False, blank=True, default=0)
    subrevision = models.IntegerField(null=False, default=0)
    latest = models.BooleanField(null=False, blank=True, default=True)
    pedagogy_tags = models.ManyToManyField("QuestionTags.PedagogyTag", blank=True)

    # TODO: how to make this work?  never seems to be called...
    # TODO: can we do the range checks on versions here?  cheaply?
    # def clean_versions(self):
    #     print(self.cleaned_data["versions"])
    #     print("TODO: ensure positive integers etc")
    #     return self.cleaned_data

    def __str__(self) -> str:
        """Return a string representation of the rubric.

        This is used when debugging and in the Django admin view.
        """
        if self.text == ".":
            return f"[{self.display_delta}]"
        if self.display_delta == ".":
            return f"{self.text}"
        return f"[{self.display_delta}] {self.text}"

    def get_absolute_url(self):
        """Return the URL to the detail view for this rubric.

        This is some internal Django stuff.   Importantly, it doesn't seem to be the full
        URL including proxied hostname or other things we cannot know but just returns
        a nice simply string like "/rubrics/42/".  Why precisely we have this method or
        what purposes it serves is left as an exercise to some future maintainer as the
        current author does not know wtf is going on here, just that its not as scary as
        the name implies.
        """
        return reverse("rubric_item", kwargs={"rid": self.rid})

    # class Meta:
    #     constraints = [
    #         # This constraint checks that each rid-revision pair is unique
    #         # TODO: this conflicts with the serializer in modify_rubric b/c the
    #         # serializer checks this constraint before we decide if we're overwriting
    #         # or making a new rubric.
    #         # models.UniqueConstraint(
    #         #     fields=["rid", "revision"], name="unique_revision_per_rid"
    #         # ),
    #         # This constraint checks that each rid has only one rubric where latest=True
    #         # TODO: unclear where "at most one" or "exactly one"
    #         # TODO: seems to conflict with RubricService.modify_rubric or maybe the serializer
    #         # models.UniqueConstraint(
    #         #     fields=["rid"], condition=Q(latest=True), name="unique_latest_per_rid"
    #         # ),
    #     ]

    # TODO: issue #3648, seeking a way to display how often they are used
    # def get_usage_count(self) -> int:
    #     return 42


class RubricPane(models.Model):
    """A user's configuration for the 'rubrics' pane in the annotation window."""

    user = models.ForeignKey(User, null=False, on_delete=models.CASCADE)
    question = models.PositiveIntegerField(default=0)
    data = models.JSONField(null=False, default=dict)


# TODO: why does this live here in models?  Why can't I build this in a service
# with "normal" prefetch etc for efficiency instead of whatever special pixie
# dust is driving this?  What makes it so special to live here in the model?
class RubricTable(django_tables2.Table):
    """Table class for displaying rubrics.

    More information on django-tables2 can be found at:
    https://django-tables2.readthedocs.io/en/latest
    """

    rid = django_tables2.Column("rid", linkify=True)
    # prevent newlines from rendering in json fields
    parameters = django_tables2.JSONColumn(json_dumps_kwargs={})
    # TODO: issue #3648, seeking a way to display how often they are used
    # times_used = django_tables2.Column(
    #     verbose_name="# Used",
    #     accessor="get_usage_count",
    #     orderable=False
    # )
    # TODO: accessor="annotations__xxx__xxx" somehow?
    # TODO: i want to make sortable but it just crashes unless orderable=False

    class Meta:
        model = Rubric

        # which fields to include in the table.  Or omit for all fields
        # and use equence = (...) to control the order.
        fields = (
            "rid",
            "display_delta",
            "last_modified",
            "revision",
            "subrevision",
            "kind",
            "system_rubric",
            "question_index",
            "text",
            "versions",
            "parameters",
            "tags",
            "pedagogy_tags",
        )
