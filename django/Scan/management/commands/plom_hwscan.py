# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Brennen Chiu
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2023 Colin B. Macdonald

from datetime import datetime
import hashlib
import pathlib

import fitz
from django.utils import timezone
from django.utils.text import slugify
from django.core.management.base import BaseCommand, CommandError

from Scan.services import ScanService


class Command(BaseCommand):
    """
    Replacement for legacy's plom-hwscan

    Not keen on name "hwscan": maybe this should be called "single-scan"?
    Or "paper-scan".  Leaning toward "paper-scan" in contrast with "bundle-scan"
    (which has its own command line tools).

    Design::

        python3 manage.py hwscan foo.pdf --sid 12345678
        python3 manage.py hwscan foo.pdf --sid 12345678 -q "[[1],[1,2],[2,3],[4]]"
        python3 manage.py hwscan foo.pdf --sid 12345678 -q all

    I'd like to support q1.pdf, q2.pdf from one person::

        python3 manage.py hwscan q1.pdf -q 1 --sid 12345678
        python3 manage.py hwscan q2.pdf -q 2 --sid 12345678

    Are there situations where we know the paper number?::

        python3 manage.py hwscan foo.pdf --paper-number 1234 -q all

    Perhaps we should use some query command to get the paper number and require
    other commands to use that (or ``--sid`` is just a helper to do that for you).

    Maybe we have an unknown paper with no obvious name, place in
    an unused papernumber or maybe create a new one (safest?)::

        python3 manage.py hwscan foo.pdf -q all --unused-paper-num

    Unlikely but possible: in multiversion mode, you'll have to tell us
    the versions of the questions (for DB row creation reasons)::

        python3 manage.py hwscan foo.pdf -q all --unused-paper-num --versions

    (people use versions for different things other than randomly: its
    not impossible to know).
    """

    help = "Upload a single paper or single question or single page for a particular student"

    # TODO: mostly just a copy paste from plom_staging_bundles
    def upload_pdf(self, source_pdf, *, username=None, questions=None):
        """Upload a pdf file

        Args:
            source_pdf (str/pathlib.Path)

        Keyword Args:
            username (str?): TODO
            questions (str/list): Can the be string "all" or a list of lists.
                TODO: more detail, but generally similar to `plom.scan` tools
                that deal with "homework pages".

        Notes::

        * currently opens all-at-once into bytes.  any memory concerns?
        """
        source_pdf = pathlib.Path(source_pdf)
        scanner = ScanService()

        try:
            with open(source_pdf, "rb") as f:
                file_bytes = f.read()
        except OSError as err:
            raise CommandError(err)

        try:
            pdf_doc = fitz.open(stream=file_bytes)
        except fitz.FileDataError as err:
            raise CommandError(err)

        slug = slugify(source_pdf.stem)
        timestamp = datetime.timestamp(timezone.now())
        hashed = hashlib.sha256(file_bytes).hexdigest()
        number_of_pages = pdf_doc.page_count

        # TODO: add a --force?  duplicates are explicitly possible for 'hw mode'
        # although we may want to LOUDLY know about them...
        if scanner.check_for_duplicate_hash(hashed):
            raise CommandError("Upload failed - Bundle was already uploaded.")
        try:
            scanner.upload_bundle_cmd(
                source_pdf, slug, username, timestamp, hashed, number_of_pages
            )
        except ValueError as err:
            raise CommandError(err)
        self.stdout.write(f"Uploaded {source_pdf} as user {username}")

        # We (probably) want to push directly...  is that possible?  Or can/should
        # we bipass the staging area altogether?  What could go wrong?
        # try:
        #     scanner.push_bundle_cmd(bundle_name)
        # except ValueError as err:
        #    raise CommandError(err)
        # self.stdout.write(f"Pushed {bundle_name}")

    def add_arguments(self, parser):
        parser.add_argument(
            "--username", nargs=1, type=str, help="Which username to upload as."
        )
        parser.add_argument("source_pdf", type=str, help="The test pdf to upload.")

        parser.add_argument("--list", help="(TODO?) List bundles.")

        parser.add_argument(
            "-q",
            "--question",
            nargs=1,
            metavar="N",
            action="store",
            help="""
                Which question(s) are answered in file.
                You can pass a single integer, or a list like `-q [1,2,3]`
                which updates each page to questions 1, 2 and 3.
                You can also pass the special string `-q all` which uploads
                each page to all questions.
                If you need to specify questions per page, you can pass a list
                of lists: each list gives the questions for each page.
                For example, `-q [[1],[2],[2],[2],[3]]` would upload page 1 to
                question 1, pages 2-4 to question 2 and page 5 to question 3.
                A common case is `-q [[1],[2],[3]]` to upload one page per
                question.
            """,
        )

    def handle(self, *args, **options):
        self.print_help("manage.py", "plom_hwscan")
