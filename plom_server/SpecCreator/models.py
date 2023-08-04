# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2022 Colin B. Macdonald

import pathlib
import shutil

from django.db import models
from django.db.models.signals import pre_delete

from Base.models import SingletonBaseModel


# just a simple folder for media for now
def temp_filename_path(instance, filename):
    return pathlib.Path("spec_reference.pdf")


class ReferencePDF(models.Model):
    # TODO: use TextField instead of CharField, don't hardcode field lengths!
    filename_slug = models.TextField(default="")
    pdf = models.FileField(upload_to=temp_filename_path)
    num_pages = models.IntegerField(default=0)


def pre_delete_reference_pdf(sender, instance, **kwargs):
    # delete thumbnails
    thumbnail_folder = (
        pathlib.Path("static") / "SpecCreator" / "thumbnails" / "spec_reference"
    )
    if thumbnail_folder.exists():
        shutil.rmtree(thumbnail_folder)

    # delete pdf from disk
    pdf_path = pathlib.Path("spec_reference.pdf")
    pdf_path.unlink(missing_ok=True)


pre_delete.connect(pre_delete_reference_pdf, sender=ReferencePDF)


class TestSpecInfo(models.Model):
    long_name = models.TextField()
    short_name = models.TextField()
    n_versions = models.PositiveIntegerField(default=0)
    n_to_produce = models.IntegerField(default=-1)
    n_questions = models.IntegerField(default=0)
    total_marks = models.IntegerField(default=0)
    pages = models.JSONField(default=dict)
    dnm_page_submitted = models.BooleanField(default=False)
    validate_page_submitted = models.BooleanField(default=False)


SHUFFLE_CHOICES = (("S", "Shuffle"), ("F", "Fix"))


# TODO: enforce field lengths in the form, not the database?
class TestSpecQuestion(models.Model):
    index = models.PositiveIntegerField(default=1)
    label = models.TextField()
    mark = models.PositiveIntegerField(default=0)
    shuffle = models.BooleanField(default=None, null=True)


class StagingSpecification(SingletonBaseModel):
    """Store the current state of the test specification as the user creates it.

    Not necessarily a valid spec - at the end of
    the specification creator wizard, the information stored here
    will be validated + converted to a JSON object
    """

    name = models.TextField(default="")
    longName = models.TextField(default="")
    numberOfPages = models.PositiveIntegerField(default=0)
    numberOfVersions = models.PositiveIntegerField(default=0)
    totalMarks = models.PositiveIntegerField(default=0)
    numberOfQuestions = models.PositiveIntegerField(default=0)
    pages = models.JSONField(default=dict)
    questions = models.JSONField(default=dict)
