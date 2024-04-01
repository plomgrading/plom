# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2023-2024 Colin B. Macdonald

import logging
from typing import List

from django.db import transaction

from ..models import Paper, FixedPage, QuestionPage

log = logging.getLogger("PaperInfoService")


class PaperInfoService:
    @transaction.atomic
    def how_many_papers_in_database(self):
        """How many papers have been created in the database."""
        return Paper.objects.count()

    @transaction.atomic
    def is_paper_database_populated(self):
        """True if any papers have been created in the DB.

        The database is initially created with empty tables.  Users get added.
        This function still returns False.  Eventually Tests (i.e., "papers")
        get created.  Then this function returns True.
        """
        return Paper.objects.filter().exists()

    def is_this_paper_in_database(self, paper_number):
        """Check if the given paper is in the database."""
        return Paper.objects.filter(paper_number=paper_number).exists()

    @transaction.atomic
    def which_papers_in_database(self) -> List:
        """List which papers have been created in the database."""
        return list(Paper.objects.values_list("paper_number", flat=True))

    def page_has_image(self, paper_number, page_number) -> bool:
        """Return True if a page has an Image associated with it."""
        paper = Paper.objects.get(paper_number=paper_number)
        page = FixedPage.objects.get(paper=paper, page_number=page_number)
        return page.image is not None

    @transaction.atomic
    def get_version_from_paper_page(self, paper_number: int, page_number: int) -> int:
        """Given a paper_number and page_number, return the version of that page.

        .. warning::
            This is a bit poorly defined; if two questions share a page
            their versions could (theoretically) differ.  Our tooling
            does not allow this situation but someone doing something
            exotic creating their own PDF tests could: they will get
            a NotImplementedError.

        Args:
            paper_number: which paper.
            page_number: which page.

        Returns:
            The version.

        Raises:
            ValueError: paper and/or page does not exist.
            NotImplementedError: multiple versions on the page that do not agree.
        """
        try:
            paper = Paper.objects.get(paper_number=paper_number)
        except Paper.DoesNotExist:
            raise ValueError(f"Paper {paper_number} does not exist in the database.")
        pages = FixedPage.objects.filter(paper=paper, page_number=page_number)
        if not pages:
            raise ValueError(
                f"Page {page_number} of paper {paper_number} does not exist in the database."
            )
        vers = [pg.version for pg in pages]
        try:
            (ver,) = set(vers)
            return ver
        except ValueError:
            raise NotImplementedError(
                f"Heterogenous versions per page not supported: got versions {vers}"
                f" for page {page_number} of paper {paper_number}"
            ) from None

    @transaction.atomic
    def get_version_from_paper_question(
        self, paper_number: int, question_idx: int
    ) -> int:
        """Given a paper number and question index, return the version of that question."""
        try:
            paper = Paper.objects.get(paper_number=paper_number)
        except Paper.DoesNotExist:
            raise ValueError(f"Paper {paper_number} does not exist in the database.")
        try:
            # to find the version, find the first fixed question page of that paper/question
            # and extract the version from that. Note - use "filter" and not "get" here.
            # TODO: why not .first()?
            page = QuestionPage.objects.filter(
                paper=paper, question_index=question_idx
            )[0]
            # This will either fail with a does-not-exist or index-out-of-range
        except (QuestionPage.DoesNotExist, IndexError):
            raise ValueError(
                f"Question {question_idx} of paper {paper_number}"
                " does not exist in the database."
            )
        return page.version
