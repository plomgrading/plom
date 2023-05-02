# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2023 Andrew Rechnitzer

from django.db import transaction

from Papers.models import Paper, FixedPage, QuestionPage, Image


class PageDataService:
    """
    Class to encapsulate functions for selecting page data and
    sending it to the client.
    """

    def get_question_order(self, page, question_pages):
        """
        Get the order of this page in a question group. i.e.,
        if this is the 2nd page of question 5, return 2.

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
        """
        Return a list of lists containing an image public key and its hash.

        Args:
            paper (int): test-paper number
            question (int): question number
        """
        test_paper = Paper.objects.get(paper_number=paper)
        question_pages = QuestionPage.objects.filter(
            paper=test_paper, question_number=question
        )

        page_list = []
        for page in question_pages.order_by("page_number"):
            image = page.image
            if image:
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

        return page_list

    @transaction.atomic
    def get_question_pages_metadata(self, paper, question=None):
        """
        Return a list of metadata for all pages in a particular paper, optionally highlighting a question.

        Args:
            paper (int): test-paper number
            question (int/None): question number, if not None.

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
        """

        test_paper = Paper.objects.get(paper_number=paper)
        paper_pages = FixedPage.objects.filter(paper=test_paper)

        pages_metadata = []
        for page in paper_pages:
            if page.image:
                if question is None:
                    # TODO: or is it better to not include this key?  That's likely
                    # what the legacy server does...
                    included = True
                else:
                    if type(page) == QuestionPage:
                        included = page.question_number == question
                    else:
                        included = False
                pages_metadata.append(
                    {
                        "pagename": f"t{page.page_number}",
                        "md5": page.image.hash,
                        "included": included,
                        "order": page.page_number,
                        "id": page.image.pk,
                        "orientation": page.image.rotation,
                        "server_path": str(page.image.image_file.path),
                    }
                )
                # TODO: handle extra + homework pages

        return pages_metadata

    @transaction.atomic
    def get_image_path(self, pk, img_hash):
        """
        Return the path to a page-image from its public key and hash.

        Args:
            pk (int): image's public key
            img_hash (str): image's hash
        """

        image = Image.objects.get(pk=pk, hash=img_hash)
        return image.image_file.path
