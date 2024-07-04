# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2023 Brennen Chiu
# Copyright (C) 2023-2024 Colin B. Macdonald
# Copyright (C) 2023 Julian Lapenna
# Copyright (C) 2023 Natalie Balashov
# Copyright (C) 2024 Aden Chan

import random

from django.db import models
from django.contrib.auth.models import User
from Mark.models.annotations import Annotation
from django.utils.translation import gettext_lazy as _


def generate_key():
    return "".join([str(random.randint(0, 9)) for i in range(12)])


def generate_unique_key():
    key = generate_key()
    existing_keys = Rubric.objects.all().values_list("key", flat=True)
    while key in existing_keys:
        key = generate_key()
    return key


class Rubric(models.Model):
    """Represents a marker's comment and mark delta for a particular question.

    Fields:
        key: is a unique key/id for accessing or uniquely identifying
            a rubric.  It is not generally (and currently isn't) the
            same as the ``pk``, which is an internal field, and
            implementation-specific.
        display_delta: short string to display, such as "+3" or "2 of 3",
            that illustrates to recipients how their score is changed by
            this rubric.
        value: the internal change associated with this rubric, not shown
            to recipients.  This should generally be somehow related to
            the display delta, although the exact calculation depends on
            ``kind`` and there maybe be hypothetical future circumstances
            such as mastery grading where the ``display_delta`` might
            differ substantially from ``value``.
        versions: a list of question versions the rubric can be used on.
        TODO: document other fields.
        annotations: a mapping to Annotation objects.  Its many-to-many
            so that multiple rubrics can link to multiple Annotations.
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

    key = models.TextField(null=False, default=generate_unique_key)
    kind = models.TextField(null=False, choices=RubricKind.choices)
    display_delta = models.TextField(null=False, default="")  # is short
    value = models.IntegerField(null=False, default=0)
    out_of = models.IntegerField(null=False, default=0)
    text = models.TextField(null=False)  # can be long
    question = models.IntegerField(null=False, default=0)
    tags = models.TextField(null=True, default="")  # can be long
    meta = models.TextField(null=True, blank=True, default="")  # can be long
    versions = models.JSONField(null=True, default=list)
    parameters = models.JSONField(null=True, default=list)
    annotations = models.ManyToManyField(Annotation, blank=True)
    system_rubric = models.BooleanField(null=False, default=False)
    published = models.BooleanField(null=False, default=True)
    # ForeignKey automatically creates a backreference from the User table
    user = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    last_modified = models.DateTimeField(auto_now=True)
    # This ``modified_by_user`` field would also automatically create a backref
    # from User which would clash with the ``user`` field.  Setting ``related_name``
    # to ``+`` prevents the backref creation, to be revisited it we need the backref
    # https://docs.djangoproject.com/en/5.0/ref/models/fields/#django.db.models.ForeignKey.related_name "
    modified_by_user = models.ForeignKey(
        User, null=True, on_delete=models.SET_NULL, related_name="+"
    )
    revision = models.IntegerField(null=False, default=0)
    latest = models.BooleanField(null=False, default=False)


class RubricPane(models.Model):
    """A user's configuration for the 'rubrics' pane in the annotation window."""

    user = models.ForeignKey(User, null=False, on_delete=models.CASCADE)
    question = models.PositiveIntegerField(default=0)
    data = models.JSONField(null=False, default=dict)
