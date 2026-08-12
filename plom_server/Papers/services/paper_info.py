# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2023-2024 Andrew Rechnitzer
# Copyright (C) 2023-2026 Colin B. Macdonald
# Copyright (C) 2026 Aidan Murphy

import logging

from django.db import transaction
from django.db.models import Count

from ..models import Paper, FixedPage
from .paper_creator import PaperCreatorService

log = logging.getLogger(__name__)


def fixedpage_version_count(page_number: int) -> dict[int, int]:
    """Get the number of papers using each version of the given page number."""
    return {
        dat["version"]: dat["count"]
        for dat in FixedPage.objects.filter(page_number=page_number)
        .values("version")
        .annotate(count=Count("version"))
    }


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
    def is_paper_database_populated() -> bool:
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
    def which_papers_in_database(self) -> list[int]:
        """List which papers have been created in the database."""
        return list(Paper.objects.values_list("paper_number", flat=True))

    @staticmethod
    @transaction.atomic
    def get_version_from_paper_page(paper_number: int, page_number: int) -> int:
        """Given a paper_number and page_number, return the version of that page.

        .. warning::
            This is a bit poorly defined; if two questions share a page
            their versions are allowed to differ.  Our tooling
            does not create this situation but someone doing something
            exotic creating their own PDF tests could: they will get a
            return value of zero.

        Args:
            paper_number: which paper.
            page_number: which page.

        Returns:
            The version, or zero if the page is multi-versioned.

        Raises:
            ValueError: paper and/or page does not exist.
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
            # Heterogeneous versions per page
            return 0

    @staticmethod
    def get_version_from_paper_question(paper_number: int, question_idx: int) -> int:
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
            page = FixedPage.objects.filter(
                page_type=FixedPage.QUESTIONPAGE,
                paper=paper,
                question_index=question_idx,
            )[0]
            # notice we use blah()[0] rather than blah.first() in order
            # to raise the exception. blah.first() will return None if
            # no such object exists. Hence this will either fail with
            # a does-not-exist or index-out-of-range
        except (FixedPage.DoesNotExist, IndexError):
            raise ValueError(
                f"Question {question_idx} of paper {paper_number}"
                " does not exist in the database."
            )
        return page.version

    @staticmethod
    def get_paper_numbers_containing_page(
        page_number: int,
        *,
        version: int | None = None,
        scanned: bool = True,
        limit: int | None = None,
    ) -> list[int]:
        """Return a sorted list of paper numbers that contain a particular page number and optionally, version.

        Note: the paper numbers are ensured to be unique

        Args:
            page_number: which page number.

        Keyword Args:
            version: which version, if omitted (or None) then return paper numbers
                independent of version.
            scanned: By default, we only return paper numbers based on FixedPage
                objects that have actually been scanned.  If False, then return
                more results (TODO: presumably from all rows of the paper database).
                but be aware that these papers might be partially (or perhaps, TODO)
                not all all scanned.
            limit: At most how many unique papers to be returns. If not provided, then return all papers
        """
        if scanned:
            query = FixedPage.objects.filter(
                page_number=page_number, image__isnull=False
            )
        else:
            query = FixedPage.objects.filter(page_number=page_number)
        if version is not None:
            query = query.filter(version=version)
        # Note lazy evaluation: no query should be actually performed until now
        unsorted = list(
            query.prefetch_related("paper")
            .values_list("paper__paper_number", flat=True)
            .distinct()
        )

        return sorted(unsorted if not limit else unsorted[:limit])

    @staticmethod
    def get_pqv_map_dict() -> dict[int, dict[int | str, int]]:
        """Get the paper-question-version mapping as a dict.

        Note if there is no version map (no papers) then this returns
        an empty dict.  If you'd prefer an error message you have to
        check for the empty return yourself.

        Returns:
            A dict of dicts, keyed first by paper number (int) and then
            by question index (int) and the string ``"id"``.  The values
            are the int versions.
        """
        pqvmapping: dict[int, dict[int | str, int]] = {}
        with transaction.atomic():
            fixedpage_queryset = (
                FixedPage.objects.all()
                .prefetch_related("paper")
                .order_by("paper__paper_number")
            )
            # force evaluation here so we get question and id pages from a single query
            # this is necessary to prevent race conditions, along with locks on fixedpage rows
            list(fixedpage_queryset)

            questionpages = fixedpage_queryset.filter(page_type=FixedPage.QUESTIONPAGE)
            idpages = fixedpage_queryset.filter(page_type=FixedPage.IDPAGE)

            for qp_obj in questionpages:
                pn = qp_obj.paper.paper_number
                if pn in pqvmapping:
                    if qp_obj.question_index in pqvmapping[pn]:
                        pass
                    else:
                        pqvmapping[pn][qp_obj.question_index] = qp_obj.version
                else:
                    pqvmapping[pn] = {qp_obj.question_index: qp_obj.version}

            for idpage_obj in idpages:
                pn = idpage_obj.paper.paper_number
                pqvmapping[pn]["id"] = idpage_obj.version

            return pqvmapping
