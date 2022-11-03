# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates

from django.db import transaction
from django.db.models import Exists, OuterRef

from Papers.models import BasePage, Paper


class ManageScanService:
    """
    Functions for managing the scanning process: tracking progress,
    handling colliding pages, unknown pages, bundles, etc.
    """

    @transaction.atomic
    def get_total_pages(self):
        """
        Return the total number of pages across all test-papers in the exam.
        """

        return len(BasePage.objects.all())

    @transaction.atomic
    def get_scanned_pages(self):
        """
        Return the number of pages in the exam that have been successfully scanned and validated.
        """

        scanned = BasePage.objects.exclude(image=None)
        return len(scanned)

    @transaction.atomic
    def get_total_test_papers(self):
        """
        Return the total number of test-papers in the exam.
        """

        return len(Paper.objects.all())

    @transaction.atomic
    def get_completed_test_papers(self):
        """
        Return the number of test-papers that have been completely scanned.
        """

        incomplete_present = BasePage.objects.filter(paper=OuterRef("pk"), image=None)
        complete_papers = Paper.objects.filter(~Exists(incomplete_present))

        return len(complete_papers)

    @transaction.atomic
    def get_test_paper_list(self):
        """
        Return a list of test-papers and their scanning completion status.
        """

        papers = Paper.objects.all()

        test_papers = []
        for tp in papers:
            paper = {}
            pages = BasePage.objects.filter(paper=tp)
            image_list = pages.values_list("image", flat=True)
            is_incomplete = pages.filter(image=None).exists()

            paper.update(
                {
                    "paper_number": f"{tp.paper_number:04}",
                    "pages": list(image_list),
                    "complete": not is_incomplete,
                }
            )
            test_papers.append(paper)

        return test_papers
