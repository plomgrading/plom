# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2023 Colin B. Macdonald

from dataclasses import dataclass
from typing import List

from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist

from Papers.services import SpecificationService
from Papers.models import (
    Paper,
    FixedPage,
    IDPage,
    DNMPage,
    QuestionPage,
    Image,
    MobilePage,
)


@dataclass()
class PageDataForTask:
    """Represents data for a single page related to a task.

    This data is sent to the marking client in order to create
    annotation images.
    """

    id: int
    md5: str
    orientation: int
    server_path: str
    included: bool
    order: int


@transaction.atomic
def get_question_pages_list(paper: int, question: int) -> List[PageDataForTask]:
    """Return a list of objects containing an image public key and its hash.

    Args:
        paper (int): test-paper number
        question (int): question number
    """
    test_paper = Paper.objects.get(paper_number=paper)
    question_pages = QuestionPage.objects.filter(
        paper=test_paper, question_number=question
    ).prefetch_related("image")
    mobile_pages = MobilePage.objects.filter(
        paper=test_paper, question_number=question
    ).prefetch_related("image")

    page_list = []
    for page in question_pages.order_by("page_number"):
        image = page.image
        if image:  # fixed pages might not have image if yet to be scanned.
            page_list.append(
                PageDataForTask(
                    id=image.pk,
                    md5=image.hash,
                    orientation=image.rotation,
                    server_path=image.image_file.path,
                    included=True,
                    order=page.page_number,
                )
            )
    # TODO - decide better order (see hackery comments below).
    # Also - do not repeat mobile pages if can avoid it.
    for page in mobile_pages:
        image = page.image
        assert image is not None  # mobile pages will always have images
        page_list.append(
            {
                "id": image.pk,
                "md5": image.hash,
                "orientation": image.rotation,
                "server_path": image.image_file.path,
                "included": True,
                # BEGIN HACKERY
                "order": len(page_list) + 1,
                # END HACKERY
            }
        )

    return page_list


class PageDataService:
    """Class to encapsulate functions for selecting page data and sending it to the client."""

    def get_question_order(self, page, question_pages):
        """Get the order of this page in a question group.

        i.e., if this is the 2nd page of question 5, return 2.

        Args:
            page: a reference to FixedPage
            question_pages: a QuerySet of FixedPages
        """
        page_number = page.page_number
        all_page_numbers = question_pages.values_list("page_number", flat=True)
        offset = min(all_page_numbers) - 1
        return page_number - offset

    @transaction.atomic
    def get_question_pages_list(self, paper, question):
        """Return a list of lists containing an image public key and its hash.

        Args:
            paper (int): test-paper number
            question (int): question number
        """
        test_paper = Paper.objects.get(paper_number=paper)
        question_pages = QuestionPage.objects.filter(
            paper=test_paper, question_number=question
        ).prefetch_related("image")
        mobile_pages = MobilePage.objects.filter(
            paper=test_paper, question_number=question
        ).prefetch_related("image")

        page_list = []
        for page in question_pages.order_by("page_number"):
            image = page.image
            if image:  # fixed pages might not have image if yet to be scanned.
                page_list.append(
                    {
                        "id": image.pk,
                        "md5": image.hash,
                        "orientation": image.rotation,
                        "server_path": image.image_file.path,
                        "included": True,
                        "order": page.page_number,
                    }
                )
        # TODO - decide better order.
        # Also - do not repeat mobile pages if can avoid it.
        for page in mobile_pages:
            image = page.image
            assert image is not None  # mobile pages will always have images
            page_list.append(
                {
                    "id": image.pk,
                    "md5": image.hash,
                    "orientation": image.rotation,
                    "server_path": image.image_file.path,
                    "included": True,
                    # WARNING - HACKERY HERE
                    "order": len(page_list) + 1,
                    # WARNING HACKERY HERE
                }
            )

        return page_list

    @transaction.atomic
    def get_question_pages_metadata(
        self, paper, *, question=None, include_idpage=False, include_dnmpages=True
    ):
        """Return a list of metadata for all pages in a paper.

        Args:
            paper (int): test-paper number
            question (int/None): question number, if not None.
            include_idpage (bool): whether to include ID pages in this
                request (default: False)
            include_dnmpages (bool): whether to include any DNM pages in
                this request (default: True)

        The ``included`` key is not meaningful if ``question`` was not passed.

        Returns:
            list, e.g. [
                {
                    'pagename': (str) 't{page_number}' for test-pages, 'e{page_number}' for extra pages, etc,
                    'md5': (str) image hash,
                    'included' (bool) was this included in the original question?,
                    'order' (int) order within a question,
                    'id' (int) image public key,
                    'orientation' (int) image orientation,
                    'server_path' (str) path to the image in the server's filesystem,
                }
            ]

        Raises:
            ObjectDoesNotExist: paper does not exist or question is out of range.
        """
        test_paper = Paper.objects.get(paper_number=paper)
        pages_metadata = []

        # loops below do not actually check if the question is valid: do that first
        if question is not None:
            numq = SpecificationService.get_n_questions()
            if question not in range(1, numq + 1):
                raise ObjectDoesNotExist(
                    f"question {question} is out of bounds [1, {numq}]"
                )

        # get all the fixed pages of the test that have images - prefetch the related image
        fixed_pages = FixedPage.objects.filter(
            paper=test_paper, image__isnull=False
        ).prefetch_related("image")

        # possibly filter out ID and DNM pages
        if not include_idpage:
            fixed_pages = fixed_pages.not_instance_of(IDPage)
        if not include_dnmpages:
            fixed_pages = fixed_pages.not_instance_of(DNMPage)

        for page in fixed_pages:
            if question is None:
                # TODO: or is it better to not include this key?  That's likely
                # what the legacy server does...
                included = True
            else:
                if isinstance(page, QuestionPage):
                    included = page.question_number == question
                else:
                    included = False
            if isinstance(page, QuestionPage):
                prefix = "t"
            elif isinstance(page, IDPage):
                prefix = "id"
            elif isinstance(page, DNMPage):
                prefix = "dnm"
            else:
                raise NotImplementedError(f"Page type {type(page)} not handled")
            pages_metadata.append(
                {
                    "pagename": f"{prefix}{page.page_number}",
                    "md5": page.image.hash,
                    "included": included,
                    "order": page.page_number,
                    "id": page.image.pk,
                    "orientation": page.image.rotation,
                    "server_path": str(page.image.image_file.path),
                }
            )

        # make a dict which counts how many mobile pages for each
        # question as we iterate through the list. We use this so that
        # we can "name" each mobile page according to both its
        # question number, and its order within the mobiles pages for
        # that question. Hence mobile pages for question 2 would be named as
        # e2.1, e2.2, e2.3, and so on.
        # but since those pages are not necessarily in order in the system we
        # need to keep count as we go.
        question_mobile_page_count = {}

        # add mobile-pages in pk order (is creation order)
        for page in (
            MobilePage.objects.filter(paper=test_paper)
            .order_by("pk")
            .prefetch_related("image")
        ):
            question_mobile_page_count.setdefault(page.question_number, 0)
            question_mobile_page_count[page.question_number] += 1
            pages_metadata.append(
                {
                    "pagename": f"e{page.question_number}.{question_mobile_page_count[page.question_number]}",
                    "md5": page.image.hash,
                    "included": page.question_number == question,
                    # WARNING - HACKERY HERE vvvvvvvv
                    "order": len(pages_metadata) + 1,
                    # WARNING - HACKERY HERE ^^^^^^^^
                    "id": page.image.pk,
                    "orientation": page.image.rotation,
                    "server_path": str(page.image.image_file.path),
                }
            )

        return pages_metadata

    @transaction.atomic
    def get_image_path(self, pk, img_hash):
        """Return the path to a page-image from its public key and hash.

        Args:
            pk (int): image's public key
            img_hash (str): image's hash
        """
        image = Image.objects.get(pk=pk, hash=img_hash)
        return image.image_file.path
