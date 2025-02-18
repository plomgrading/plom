# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2023-2025 Colin B. Macdonald

from typing import Any

from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist
from django.core.files import File

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


@transaction.atomic
def get_question_pages_list(paper: int, question_index: int) -> list[dict[str, Any]]:
    """Return a list of objects describing pages in a paper related to a question.

    Args:
        paper: exam paper number.
        question_index: which question.
    """
    test_paper = Paper.objects.get(paper_number=paper)
    question_pages = QuestionPage.objects.filter(
        paper=test_paper, question_index=question_index
    ).prefetch_related("image")
    mobile_pages = MobilePage.objects.filter(
        paper=test_paper, question_index=question_index
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
                    # For Future us vvvvv ?
                    # "img_height": image.height, "img_width": image.width,
                    # For Future us ^^^^^ ?
                    # We may wish to also pass height/width info
                    # if we do so then we need to confirm how django automagically computes
                    # these for the imagefield - they are raw image height/width before any
                    # exif or plom rotations. So will need to document precisely what these
                    # are for any consumers of this API.
                }
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
                # For Future us vvvvv ?
                # "img_height": image.height, "img_width": image.width,
                # For Future us ^^^^^ ?
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
    def get_question_pages_metadata(
        self,
        paper: int,
        *,
        question: int | None = None,
        include_idpage: bool = False,
        include_dnmpages: bool = True,
    ) -> list[dict[str, Any]]:
        """Return a list of metadata for all pages in a paper.

        The pages are "in order".  FixedPages ("expected" pages that have
        QR-codes and predictable positions in the paper) will appear in
        order of their page number.  MobilePages will appear after the
        FixedPages.

        Args:
            paper (int): test-paper number

        Keyword Args:
            question (int/None): question index, if not None.
            include_idpage (bool): whether to include ID pages in this
                request (default: False)
            include_dnmpages (bool): whether to include any DNM pages in
                this request (default: True)

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
            The ``included`` key is not meaningful if ``question`` was not passed.

        Raises:
            ObjectDoesNotExist: paper does not exist or question is out of range.
        """
        test_paper = Paper.objects.get(paper_number=paper)
        pages_metadata = []

        # loops below do not actually check if the question is valid: do that first
        if question is not None:
            question_indices = SpecificationService.get_question_indices()
            if question not in question_indices:
                raise ObjectDoesNotExist(
                    f"question {question} is out of bounds {question_indices}"
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

        for page in fixed_pages.order_by("page_number"):
            if question is None:
                # TODO: or is it better to not include this key?  That's likely
                # what the legacy server does...
                included = True
            else:
                if isinstance(page, QuestionPage):
                    included = page.question_index == question
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
        # question index, and its order within the mobiles pages for
        # that question. Hence mobile pages for question 2 would be named as
        # e2.1, e2.2, e2.3, and so on.
        # but since those pages are not necessarily in order in the system we
        # need to keep count as we go.
        question_mobile_page_count: dict[int, int] = {}

        # add mobile-pages in pk order (is creation order)
        for page in (
            MobilePage.objects.filter(paper=test_paper)
            .order_by("pk")
            .prefetch_related("image")
        ):
            qidx = page.question_index
            question_mobile_page_count.setdefault(qidx, 0)
            question_mobile_page_count[qidx] += 1
            if qidx == MobilePage.DNM_qidx:
                pagename = f"ednm.{question_mobile_page_count[qidx]}"
            else:
                pagename = f"e{qidx}.{question_mobile_page_count[qidx]}"
            pages_metadata.append(
                {
                    "pagename": pagename,
                    "md5": page.image.hash,
                    "included": qidx == question,
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
    def get_page_image(self, pk: int, *, img_hash: str | None = None) -> File:
        """Return the path to a page-image from its public key and hash.

        Args:
            pk: image's public key

        Keyword Args:
            img_hash: optionally the image's hash.

        Returns:
            A Django file object.

        Raises:
            ObjectDoesNotExist: no such page image or hash does not match.
        """
        if img_hash:
            image = Image.objects.get(pk=pk, hash=img_hash)
        else:
            image = Image.objects.get(pk=pk)
        return image.image_file
