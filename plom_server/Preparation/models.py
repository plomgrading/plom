# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2024 Andrew Rechnitzer
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2023-2025 Colin B. Macdonald
# Copyright (C) 2024 Aden Chan
# Copyright (C) 2024 Aidan Murphy

from django.db import models


class PaperSourcePDF(models.Model):
    version = models.PositiveIntegerField(unique=True)
    source_pdf = models.FileField(upload_to="sourceVersions/")
    pdf_hash = models.CharField(null=False, max_length=64)
    original_filename = models.TextField()


# ---------------------------------
# Make a table for students - for the purposes of preparing things. Hence "staging" prefix.


class StagingStudent(models.Model):
    """Table of student information for potential prenaming.

    Note, name is stored as a single field.

    student_id (str): The students id-number or id-string. Must be unique.
    student_name (str): The name of the student (as a single text field).
    paper_number (int/None): Optional paper number assigned to (predicted) for
        this student.  This is used for prenaming - not linked to the
        actual DB for papers.  Certain "sentinel" values are accepted to
        mean "None", these include ``None``, ``-1``, and ``""``, although
        this is enforced in code that creates rows rather than a serializer.
    """

    # To understand why a single name-field, see
    # https://www.kalzumeus.com/2010/06/17/falsehoods-programmers-believe-about-names/

    # to allow for case where we know name but not id.
    student_id = models.TextField(null=True, unique=True)
    # must have unique id.
    student_name = models.TextField(null=False)
    # optional paper-number for prenaming
    # Note: PositiveIntegerField means NonNegative
    paper_number = models.PositiveIntegerField(null=True)


class StagingPQVMapping(models.Model):
    """Table to store the test-question-version mapping for staging.

    Store as triples of paper-question-version. This is very loose,
    but avoids recreating the entire paper-structure.
    """

    paper_number = models.PositiveIntegerField(null=False)
    question = models.PositiveIntegerField(null=False)
    version = models.PositiveIntegerField(null=False)
