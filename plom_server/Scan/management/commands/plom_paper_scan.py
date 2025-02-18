# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Brennen Chiu
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2023-2025 Colin B. Macdonald

from tabulate import tabulate

from django.core.management.base import BaseCommand, CommandError

from ...services import ScanService


class Command(BaseCommand):
    """Plom Paper Scan deals with single papers, in contrast with Plom Staging Bundle.

    This is a replacement for the legacy ``plom-hwscan``, it can be used to push
    a file to particular paper number and to one or more questions.

    Because upload starts a background job, we do this in two steps, first push a bundle::

        python3 manage.py plom_staging_bundles upload foo.pdf

    Then we can map that bundle onto paper numbers and questions::

        python3 manage.py plom_paper_scan list_bundles
        python3 manage.py plom_paper_scan map foo --papernum 1234 --question all
        python3 manage.py plom_paper_scan map foo -t 20 -q [[1],[2],[2],[2],[3],[3]]

    (currently "all" is broken and we can't share pages between questions.)

    Other design ideas, not implemented yet::

        python3 manage.py plom_paper_scan foo.pdf --sid 12345678
        python3 manage.py plom_paper_scan foo.pdf --sid 12345678 -q "[[1],[1,2],[2,3],[4]]"
        python3 manage.py plom_paper_scan foo.pdf --sid 12345678 -q all

    I'd like to support q1.pdf, q2.pdf from one person::

        python3 manage.py plom_paper_scan q1.pdf -q 1 --sid 12345678
        python3 manage.py plom_paper_scan q2.pdf -q 2 --sid 12345678

    Perhaps we should use some query command to get the paper number and require
    other commands to use that (or ``--sid`` is just a helper to do that for you).

    Maybe we have an unknown paper with no obvious name, place in
    an unused papernumber or maybe create a new one (safest?)::

        python3 manage.py plom_paper_scan foo.pdf -q all --unused-paper-num

    Unlikely but possible: in multiversion mode, you'll have to tell us
    the versions of the questions (for DB row creation reasons)::

        python3 manage.py plom_paper_scan foo.pdf -q all --unused-paper-num --versions

    (people use versions for different things other than randomly: its
    not impossible to know).
    """

    help = "Upload a single paper or single question or single page for a particular student"

    def staging_bundle_status(self):
        scanner = ScanService()
        bundle_status = scanner.staging_bundle_status()
        self.stdout.write(
            tabulate(bundle_status, headers="firstrow", tablefmt="simple_outline")
        )

    # TODO: currently, we don't have our own push: just use "plom_staging_bundles".
    # TODO: add a --force?  duplicates are explicitly possible for 'hw mode'
    # although we may want to LOUDLY know about them...

    # TODO: do we need our own "push" command or can we piggy-back on "plom_staging_bundles"?

    # TODO: longer term, might be nice to have our own, even if we just call the functions
    # from "plom_staging_bundles".

    def map_bundle_pages(
        self, bundle_name: str, *, papernum: int, questions: str | None
    ) -> None:
        if questions is None:
            questions = "all"
        # many types possible for ``questions`` but here we always get a str
        scanner = ScanService()
        try:
            scanner.map_bundle_pages_cmd(
                bundle_name=bundle_name, papernum=papernum, question_map=questions
            )
        except ValueError as err:
            raise CommandError(err)

    def add_arguments(self, parser):
        sub = parser.add_subparsers(
            dest="command",
            description="Various tasks about rubrics.",
        )

        sub.add_parser(
            "list_bundles",
            help="List bundles",
            description="List all bundles on server.",
        )

        sp_map = sub.add_parser(
            "map",
            help="Assign pages of a bundle to particular questions.",
            description="""
                Assign pages of a bundle to particular question(s),
                ignoring QR-codes etc.
            """,
        )

        # TODO: might be more robust to work with bundle IDs as well/instead?
        sp_map.add_argument("bundle_name", help="Which bundle")

        sp_map.add_argument(
            "--papernum",
            "-t",
            metavar="T",
            type=int,
            help="""
                Which paper number to upload to.
                It must exist; you must create it first with appropriate
                versions.  No mechanism exposed yet to do that...
                TODO: argparse has this as optional but no default setting
                for this yet: maybe it should assign to the next available
                paper number or something like that?
            """,
        )
        sp_map.add_argument(
            "-q",
            "--question",
            metavar="N",
            help="""
                Which question(s) are answered in file.
                You can pass a single integer, or a list like `-q [1,2,3]`
                which updates each page to questions 1, 2 and 3.
                You can also pass the special string `-q all` which uploads
                each page to all questions (this is also the default).
                If you need to specify questions per page, you can pass a list
                of lists: each list gives the questions for each page.
                For example, `-q [[1],[2],[2],[2],[3]]` would upload page 1 to
                question 1, pages 2-4 to question 2 and page 5 to question 3.
                A common case is `-q [[1],[2],[3]]` to upload one page per
                question.
                An empty list will "discard" that particular page.
            """,
        )

    def handle(self, *args, **opt) -> None:
        self.stdout.write(
            self.style.WARNING("CAUTION: paper_scan is an experimental tool")
        )

        if opt["command"] == "list_bundles":
            self.staging_bundle_status()

        if opt["command"] == "map":
            self.map_bundle_pages(
                opt["bundle_name"], papernum=opt["papernum"], questions=opt["question"]
            )
