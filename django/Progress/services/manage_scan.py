# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates

from django.db import transaction
from django.db.models import Exists, OuterRef

from Papers.models import BasePage, Paper, QuestionPage
from Scan.models import StagingImage


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
    def get_test_paper_list(self, exclude_complete=False, exclude_incomplete=False):
        """
        Return a list of test-papers and their scanning completion status.

        Args:
            exclude_complete (bool): if True, filter complete test-papers from the list.
            exclude_incomplete (bool): if True, filter incomplete test-papers from the list.
        """

        papers = Paper.objects.all()

        test_papers = []
        for tp in papers:
            paper = {}
            page_query = BasePage.objects.filter(paper=tp).order_by("page_number")
            is_incomplete = page_query.filter(image=None).exists()

            if (is_incomplete and not exclude_incomplete) or (
                not is_incomplete and not exclude_complete
            ):
                pages = []
                for p in page_query:
                    if type(p) == QuestionPage:
                        pages.append(
                            {
                                "image": p.image,
                                "version": p.question_version,
                                "number": p.page_number,
                            }
                        )
                    else:
                        pages.append({"image": p.image, "number": p.page_number})

                paper.update(
                    {
                        "paper_number": f"{tp.paper_number:04}",
                        "pages": list(pages),
                        "complete": not is_incomplete,
                    }
                )
                test_papers.append(paper)

        return test_papers

    @transaction.atomic
    def get_page_image(self, test_paper, index):
        """
        Return a page-image.

        Args:
            test_paper (int): paper ID
            index (int): page number
        """

        paper = Paper.objects.get(paper_number=test_paper)
        page = BasePage.objects.get(paper=paper, page_number=index)
        return page.image

    @transaction.atomic
    def get_n_colliding_pages(self):
        """
        Return the number of colliding images in the database.
        """
        colliding = StagingImage.objects.filter(colliding=True)
        return len(colliding)

    @transaction.atomic
    def get_colliding_pages_list(self):
        """
        Return a list of colliding pages.
        """

        colliding_pages = []
        colliding = StagingImage.objects.filter(colliding=True)

        for page in colliding:
            any_qr = list(page.parsed_qr.values())[0]
            test_paper = int(any_qr["paper_id"])
            page_number = int(any_qr["page_num"])
            timestamp = page.bundle.timestamp
            user = page.bundle.user.username
            order = page.bundle_order

            if any_qr["version_num"]:
                version = int(any_qr["version_num"])
            else:
                version = None

            colliding_pages.append(
                {
                    "test_paper": test_paper,
                    "number": page_number,
                    "version": version,
                    "timestamp": timestamp,
                    "user": user,
                    "order": order,
                }
            )

        return colliding_pages
