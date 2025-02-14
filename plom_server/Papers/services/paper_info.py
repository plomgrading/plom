# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2023-2024 Andrew Rechnitzer
# Copyright (C) 2023-2025 Colin B. Macdonald

import logging

from django.db import transaction

from ..models import (
    Paper,
    FixedPage,
    QuestionPage,
    NumberOfPapersToProduceSetting,
)
from .paper_creator import PaperCreatorService

log = logging.getLogger("PaperInfoService")


class PaperInfoService:
    @transaction.atomic
    def how_many_papers_in_database(self):
        """How many papers have been created in the database."""
        return Paper.objects.count()

    @staticmethod
    def is_paper_database_being_updated_in_background() -> bool:
        """Returns true when the paper-db is being updated via background tasks."""
        return PaperCreatorService.is_background_chore_in_progress()

    @staticmethod
    def is_paper_database_fully_populated() -> bool:
        """Returns true when number of papers in the database equals the number to produce."""
        nop = NumberOfPapersToProduceSetting.load().number_of_papers
        db_count = Paper.objects.count()
        if db_count > 0 and db_count == nop:
            return True
        else:
            return False

    @staticmethod
    def is_paper_database_partially_but_not_fully_populated() -> bool:
        """Returns true when number of papers in the database is positive but strictly less than the number to produce.

        TODO: currently I think this is unused.
        """
        nop = NumberOfPapersToProduceSetting.load().number_of_papers
        db_count = Paper.objects.count()
        return db_count > 0 and db_count < nop

    @staticmethod
    def is_paper_database_populated() -> bool:
        """True if any papers have been created in the DB.

        The database is initially created with empty tables.  Users get added.
        This function still returns False.  Eventually Tests (i.e., "papers")
        get created.  Then this function returns True.

        See also :method:`is_paper_database_fully_populated`.
        """
        return Paper.objects.filter().exists()

    def is_this_paper_in_database(self, paper_number):
        """Check if the given paper is in the database."""
        return Paper.objects.filter(paper_number=paper_number).exists()

    @transaction.atomic
    def which_papers_in_database(self) -> list[int]:
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
                f"Heterogeneous versions per page not supported: got versions {vers}"
                f" for page {page_number} of paper {paper_number}"
            ) from None

    def get_version_from_paper_question(
        self, paper_number: int, question_idx: int
    ) -> int:
        """Given a paper number and question index, return the version of that question.

        Raises:
            ValueError: no such paper / question_idx exists.  Typically
                because there is no such paper, or no such paper *yet*,
                but also includes the case where question_idx is out of
                bounds, for example, a non-positive integer.
        """
        try:
            paper = Paper.objects.get(paper_number=paper_number)
        except Paper.DoesNotExist:
            raise ValueError(f"Paper {paper_number} does not exist in the database.")
        try:
            # to find the version, find the first fixed question page of that paper/question
            # and extract the version from that. Note - use "filter" and not "get" here.
            page = QuestionPage.objects.filter(
                paper=paper, question_index=question_idx
            )[0]
            # notice we use blah()[0] rather than blah.first() in order
            # to raise the exception. blah.first() will return None if
            # no such object exists. Hence this will either fail with
            # a does-not-exist or index-out-of-range
        except (QuestionPage.DoesNotExist, IndexError):
            raise ValueError(
                f"Question {question_idx} of paper {paper_number}"
                " does not exist in the database."
            )
        return page.version

    @transaction.atomic
    def get_paper_numbers_containing_given_page_version(
        self, version, page_number, *, scanned=True
    ) -> list[int]:
        """Given the version and page-number, return list of paper numbers that contain that page/version."""
        if scanned:
            return sorted(
                list(
                    FixedPage.objects.filter(
                        page_number=page_number, version=version, image__isnull=False
                    )
                    .prefetch_related("paper")
                    .values_list("paper__paper_number", flat=True)
                )
            )
        else:
            return sorted(
                list(
                    FixedPage.objects.filter(page_number=page_number, version=version)
                    .prefetch_related("paper")
                    .values_list("paper__paper_number", flat=True)
                )
            )

    @staticmethod
    def get_pqv_map_dict() -> dict[int, dict[int, int]]:
        """Get the paper-question-version mapping as a dict.

        Note if there is no version map (no papers) then this returns
        an empty dict.  If you'd prefer an error message you have to
        check for the empty return yourself.
        """
        pqvmapping: dict[int, dict[int, int]] = {}
        with transaction.atomic():
            # note that this gets all question pages, not just one for each question.
            for qp_obj in (
                QuestionPage.objects.all()
                .prefetch_related("paper")
                .order_by("paper__paper_number")
            ):
                pn = qp_obj.paper.paper_number
                if pn in pqvmapping:
                    if qp_obj.question_index in pqvmapping[pn]:
                        pass
                    else:
                        pqvmapping[pn][qp_obj.question_index] = qp_obj.version
                else:
                    pqvmapping[pn] = {qp_obj.question_index: qp_obj.version}
            return pqvmapping
