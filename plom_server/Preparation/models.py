# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2024 Andrew Rechnitzer
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2023-2024 Colin B. Macdonald

from django.db import models
from django.conf import settings

from Base.models import SingletonBaseModel
from Base.models import HueyTaskTracker


class PaperSourcePDF(models.Model):
    version = models.PositiveIntegerField(unique=True)
    source_pdf = models.FileField(upload_to="sourceVersions/")
    hash = models.CharField(null=False, max_length=64)

    @classmethod
    def upload_to(cls):
        return settings.MEDIA_ROOT / cls.source_pdf.field.upload_to


class PrenamingSetting(SingletonBaseModel):
    enabled = models.BooleanField(default=False, null=False)


# TODO: consider moving this field to Base.SettingsModel
class PapersPrintedSettingModel(SingletonBaseModel):
    """Set this once user has printed papers."""

    have_printed_papers = models.BooleanField(default=False, null=False)


# ---------------------------------
# Make a table for students - for the purposes of preparing things. Hence "staging" prefix.


class StagingStudent(models.Model):
    """Table of student information for potential prenaming.

    Note, name is stored as a single field.

    student_id (str): The students id-number or id-string. Must be unique.
    student_name (str): The name of the student (as a single text field).
    paper_number (int): Optional paper_number assigned to this student. For
        prenaming - not linked to the actual DB for papers.
    """

    # To understand why a single name-field, see
    # https://www.kalzumeus.com/2010/06/17/falsehoods-programmers-believe-about-names/

    # to allow for case where we know name but not id.
    student_id = models.TextField(null=True, unique=True)
    # must have unique id.
    student_name = models.TextField(null=False)
    # optional paper-number for prenaming
    paper_number = models.PositiveIntegerField(null=True)


class StagingPQVMapping(models.Model):
    """Table to store the test-question-version mapping for staging.

    Store as triples of paper-question-version. This is very loose,
    but avoids recreating the entire paper-structure.
    """

    paper_number = models.PositiveIntegerField(null=False)
    question = models.PositiveIntegerField(null=False)
    version = models.PositiveIntegerField(null=False)


# ---------------------------------
# Make a table for the extra page pdf and the associated huey task


class ExtraPagePDFHueyTask(HueyTaskTracker):
    """Table to store the exta page pdf huey task.

    Note that this inherits fields from the base class table.  We add
    extra function to this to ensure there can only be one such task.

    There was an attempt to make a common SingletonHueyTaskTracker but
    for now we're just duplicating that here (Issue #3130).
    """

    extra_page_pdf = models.FileField(upload_to="sourceVersions/")

    def save(self, *args, **kwargs):
        ExtraPagePDFHueyTask.objects.exclude(id=self.id).delete()
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass

    @classmethod
    def load(cls):
        obj, created = ExtraPagePDFHueyTask.objects.get_or_create()
        return obj


class ScrapPaperPDFHueyTask(HueyTaskTracker):
    """Table to store the scrap paper pdf huey task.

    Note that this inherits fields from the base class table.  We add
    extra function to this to ensure there can only be one such task.

    There was an attempt to make a common SingletonHueyTaskTracker but
    for now we're just duplicating that here (Issue #3130).
    """

    scrap_paper_pdf = models.FileField(upload_to="sourceVersions/")

    def save(self, *args, **kwargs):
        ScrapPaperPDFHueyTask.objects.exclude(id=self.id).delete()
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass

    @classmethod
    def load(cls):
        obj, created = ScrapPaperPDFHueyTask.objects.get_or_create()
        return obj
