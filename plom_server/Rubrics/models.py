# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2023 Brennen Chiu
# Copyright (C) 2023-2024 Colin B. Macdonald
# Copyright (C) 2023 Julian Lapenna
# Copyright (C) 2023 Natalie Balashov
# Copyright (C) 2024 Aidan Murphy
# Copyright (C) 2024 Aden Chan

import random

from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
import django_tables2

# from django.db.models import Max
# from django.db.models.query_utils import Q

from Mark.models.annotations import Annotation


def generate_key():
    # TODO: tricky to avoid a race with this here:
    # count = Rubric.objects.aggregate(Max("key"))["key__max"]
    # return 1 if count is None else count + 1

    def _genkey():
        # unsigned intmax or something like that
        return random.randint(1, 2_100_000_000)

    # this still has a race condition, just incredibly unlikely to hit it
    key = _genkey()
    existing_keys = Rubric.objects.all().values_list("key", flat=True)
    while key in existing_keys:
        key = _genkey()
    return key


class Rubric(models.Model):
    """Represents a marker's comment and mark delta for a particular question.

    Fields:
        key: a unique key/id for accessing or uniquely identifying
            a rubric.  It is not generally (and currently isn't) the
            same as the ``pk``, which is an internal field, and
            implementation-specific. `generate_key` is only run when
            creating a new rubric, and is not run when updating an
            existing rubric via the rubric service, ensuring that
            the same key is preserved across revisions, even if
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
        question: the question this rubric is associated with.
        tags: a list of tags for this rubric.
        meta: text shown only to markers, not to students.
        versions: a list of question versions the rubric can be used on.
        parameters: a list of parameters for the rubric, used in
            parameterized rubrics.
        annotations: a mapping to Annotation objects.  Its many-to-many
            so that multiple rubrics can link to multiple Annotations.
        out_of: the maximum ``value`` an "abs" ``kind`` rubric may hold, 0 otherwise.
        text: a string to display to recipients, its format is not pre-defined.
        question: the ``SpecQuestion`` this rubric is related to.
        tags: TODO:
        meta: TODO:
        versions: a JSON list containing the versions of ``question``
            this rubric is assigned to.
        parameters: TODO:
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
        revision: a monontonically-increasing integer used to detect mid-air
            collisions.  Modifying a rubric will increase this by one.
            If you are messing with this, presumably you are doing something
            creative/hacky.
        latest: True when this is the latest version of the rubric and
            false otherwise. There will be only one latest rubric per key.
    """

    class RubricKind(models.TextChoices):
        ABSOLUTE = "absolute", _("Absolute")
        NEUTRAL = "neutral", _("Neutral")
        RELATIVE = "relative", _("Relative")

    key = models.IntegerField(null=False, default=generate_key)
    kind = models.TextField(null=False, choices=RubricKind.choices)
    display_delta = models.TextField(null=False, blank=True, default="")  # is short
    value = models.FloatField(null=False, blank=True, default=0)
    out_of = models.FloatField(
        null=False, blank=True, default=0, validators=[MinValueValidator(0.0)]
    )
    text = models.TextField(null=False)  # can be long
    question = models.IntegerField(null=False, blank=True, default=0)
    tags = models.TextField(null=True, blank=True, default="")  # can be long
    meta = models.TextField(null=True, blank=True, default="")  # can be long
    versions = models.JSONField(null=True, blank=True, default=list)
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
    latest = models.BooleanField(null=False, blank=True, default=True)
    pedagogy_tags = models.ManyToManyField("QuestionTags.PedagogyTag", blank=True)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super(Rubric, self).save(*args, **kwargs)

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
        return reverse("rubric_item", kwargs={"rubric_key": self.key})

    class Meta:
        constraints = [
            # This constraint checks that each key-revision pair is unique
            models.UniqueConstraint(
                fields=["key", "revision"], name="unique_revision_per_key"
            ),
            # This constraint checks that each key has only one rubric where latest=True
            # TODO: unclear where "at most one" or "exactly one"
            # TODO: seems to conflict with RubricService.modify_rubric or maybe the serializer
            # models.UniqueConstraint(
            #     fields=["key"], condition=Q(latest=True), name="unique_latest_per_key"
            # ),
        ]


class RubricPane(models.Model):
    """A user's configuration for the 'rubrics' pane in the annotation window."""

    user = models.ForeignKey(User, null=False, on_delete=models.CASCADE)
    question = models.PositiveIntegerField(default=0)
    data = models.JSONField(null=False, default=dict)


class RubricTable(django_tables2.Table):
    """Table class for displaying rubrics.

    More information on django-tables2 can be found at:
    https://django-tables2.readthedocs.io/en/latest
    """

    key = django_tables2.Column("Key", linkify=True)
    times_used = django_tables2.Column(verbose_name="# Used")

    class Meta:
        model = Rubric

        fields = (
            "key",
            "display_delta",
            "last_modified",
            "kind",
            "system_rubric",
            "question",
            "text",
        )
        sequence = (
            "key",
            "display_delta",
            "last_modified",
            "kind",
            "system_rubric",
            "question",
            "text",
        )
