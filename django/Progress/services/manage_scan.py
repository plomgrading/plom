# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates

import shutil

from django.db import transaction
from django.db.models import Exists, OuterRef
from django.conf import settings

from Papers.models import (
    BasePage,
    Paper,
    QuestionPage,
    CollidingImage,
    DiscardedImage,
    Image,
)
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
        colliding = CollidingImage.objects.all()
        return len(colliding)

    @transaction.atomic
    def get_colliding_pages_list(self):
        """
        Return a list of colliding pages.
        """

        colliding_pages = []
        colliding = CollidingImage.objects.all()

        for page in colliding:
            test_paper = page.paper_number
            page_number = page.page_number
            image_hash = page.hash

            version = None

            colliding_pages.append(
                {
                    "test_paper": test_paper,
                    "number": page_number,
                    "version": version,
                    "colliding_hash": image_hash,
                }
            )

        return colliding_pages

    @transaction.atomic
    def get_colliding_image(self, image_hash):
        """
        Return a colliding page.

        Args:
            image_hash: sha256 of the image.
        """
        return CollidingImage.objects.get(hash=image_hash)

    @transaction.atomic
    def get_discarded_image_path(self, image_hash, make_dirs=True):
        """
        Return a Pathlib path pointing to
        BASE_DIR/media/page_images/discarded_pages/{paper_number}/{page_number}.png

        Args:
            image_hash: str, sha256 of the discarded page
            make_dirs (optional): set to False for testing
        """

        root_folder = settings.BASE_DIR / "media" / "page_images" / "discarded_pages"
        image_path = root_folder / f"{image_hash}.png"

        if make_dirs:
            root_folder.mkdir(exist_ok=True)

        return image_path

    @transaction.atomic
    def discard_colliding_image(self, colliding_image, make_dirs=True):
        """
        Discard a colliding image.

        Args:
            colliding_image: reference to a CollidingImage instance
            make_dirs (optional): bool, set to False for testing.
        """
        image_path = self.get_discarded_image_path(colliding_image.hash)

        discarded_image = DiscardedImage(
            bundle=colliding_image.bundle,
            bundle_order=colliding_image.bundle_order,
            original_name=colliding_image.original_name,
            file_name=str(image_path),
            hash=colliding_image.hash,
            rotation=colliding_image.rotation,
        )

        staged_image = StagingImage.objects.get(
            bundle__pdf_hash=colliding_image.bundle.hash,
            bundle_order=colliding_image.bundle_order,
        )
        staged_image.colliding = False
        staged_image.save()

        if make_dirs:
            shutil.move(str(colliding_image.file_name), str(image_path))

        colliding_image.delete()
        discarded_image.save()

    @transaction.atomic
    def replace_image_with_colliding(self, image, colliding_image, make_dirs=True):
        """
        Discard an Image instance and replace it with a colliding image.

        Args:
            image (Image): the currently accepted image
            colliding_image (CollidingImage): another scanned image
            make_dirs (optional): Bool, set to False for testing
        """

        discard_path = self.get_discarded_image_path(image.hash, make_dirs=make_dirs)
        discarded_page = DiscardedImage(
            bundle=image.bundle,
            bundle_order=image.bundle_order,
            original_name=image.original_name,
            file_name=str(discard_path),
            hash=image.hash,
            rotation=image.rotation,
        )

        new_image = Image(
            bundle=colliding_image.bundle,
            bundle_order=colliding_image.bundle_order,
            original_name=colliding_image.original_name,
            file_name=image.file_name,
            hash=colliding_image.hash,
            rotation=colliding_image.rotation,
        )

        image_page = BasePage.objects.get(image=image)
        image_page.image = new_image

        if make_dirs:
            shutil.move(str(image.file_name), str(discarded_page.file_name))
            shutil.move(str(colliding_image.file_name), str(new_image.file_name))

        colliding_image.delete()
        image.delete()
        discarded_page.save()
        new_image.save()
        image_page.save()
