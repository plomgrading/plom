# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2024 Andrew Rechnitzer
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2023-2026 Colin B. Macdonald
# Copyright (C) 2024 Aden Chan
# Copyright (C) 2024 Aidan Murphy

from django.db import models


class PaperSourcePDF(models.Model):
    """Describes the structure of one of the source PDF files.

    version: which version is this.
    source_pdf: the file itself, one of those magic FileField things:
        so be careful with this.
    pdf_hash: a hash, currently sha256 of the bytes of this file.
    original_filename: optional, the original file name.
    page_count: optional, how many pages in this PDF.
    paper_size_name: optional, a string for the paper size such as "letter".
        If the pages don't agree it can be set to something alarming like
        "various (!)".  This quantity is typically computed by rounding
        and comparing various page sizes against PyMuPDF's list of well-known
        page sizes; if its not recognized, it will be set to "custom".
        In any case, the next two fields might be more specific / accurate.
    paper_size_width: optional, float width in pts, generally only to
        be set if all pages agree.  This is the raw width of the first
        page of the PDF file.
    paper_size_height: optional, float height in pts, generally only to
        be set if all pages agree.  The is the raw height of the first
        page of the PDF file.
    """

    version = models.PositiveIntegerField(unique=True)
    source_pdf = models.FileField(upload_to="sourceVersions/")
    pdf_hash = models.CharField(null=False, max_length=64)
    original_filename = models.TextField()
    page_count = models.PositiveIntegerField(null=True, blank=True)
    paper_size_name = models.TextField(null=True, blank=True)
    paper_size_width = models.FloatField(null=True, blank=True)
    paper_size_height = models.FloatField(null=True, blank=True)


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
