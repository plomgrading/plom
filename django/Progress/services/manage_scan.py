# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2022 Brennen Chiu
# Copyright (C) 2023 Natalie Balashov

import shutil
import arrow
from datetime import datetime

from django.utils import timezone
from django.db import transaction
from django.db.models import Exists, OuterRef
from django.conf import settings

from Papers.models import (
    FixedPage,
    MobilePage,
    Paper,
    QuestionPage,
    DNMPage,
    IDPage,
    DiscardImage,
    Image,
)
from Scan.models import StagingImage, StagingBundle


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

        return len(FixedPage.objects.all())

    @transaction.atomic
    def get_scanned_pages(self):
        """
        Return the number of pages in the exam that have been successfully scanned and validated.
        """

        scanned = FixedPage.objects.exclude(image=None)
        return len(scanned)

    @transaction.atomic
    def get_total_test_papers(self):
        """
        Return the total number of test-papers in the exam.
        """

        return len(Paper.objects.all())

    @transaction.atomic
    def get_number_completed_test_papers(self):
        """Return a dict of completed papers and their fixed/mobile pages.

        A paper is complete when it either has **all** its fixed
        pages, or it has no fixed pages but has some extra-pages.
        """
        # Get fixed pages with no image
        fixed_with_no_scan = FixedPage.objects.filter(paper=OuterRef("pk"), image=None)
        # Get count of papers without fixed-page-with-no-scan
        all_fixed_present = Paper.objects.filter(~Exists(fixed_with_no_scan))
        # now get papers with **no** fixed page scans
        fixed_with_scan = FixedPage.objects.filter(
            paper=OuterRef("pk"), image__isnull=False
        )
        mobile_pages = MobilePage.objects.filter(paper=OuterRef("pk"))
        no_fixed_but_some_mobile = Paper.objects.filter(
            ~Exists(fixed_with_scan), Exists(mobile_pages)
        )
        return all_fixed_present.count() + no_fixed_but_some_mobile.count()

    @transaction.atomic
    def get_all_completed_test_papers(self):
        """
        Return the number of test-papers that have been completely scanned.

        A paper is complete when it either has **all** its fixed
        pages, or it has no fixed pages but has some extra-pages.
        """
        # Get fixed pages with no image
        fixed_with_no_scan = FixedPage.objects.filter(paper=OuterRef("pk"), image=None)
        # Get count of papers without fixed-page-with-no-scan
        all_fixed_present = Paper.objects.filter(~Exists(fixed_with_no_scan))
        # now get papers with **no** fixed page scans
        fixed_with_scan = FixedPage.objects.filter(
            paper=OuterRef("pk"), image__isnull=False
        )
        mobile_pages = MobilePage.objects.filter(paper=OuterRef("pk"))
        no_fixed_but_some_mobile = Paper.objects.filter(
            ~Exists(fixed_with_scan), Exists(mobile_pages)
        )

        complete = {}
        for paper in all_fixed_present:
            complete[paper.paper_number] = []
            for fp in paper.fixedpage_set.all().order_by("page_number"):
                complete[paper.paper_number].append(
                    {
                        "type": "fixed",
                        "page_number": fp.page_number,
                        "img_pk": fp.image.pk,
                    }
                )
            for mp in paper.mobilepage_set.all().order_by("question_number"):
                complete[paper.paper_number].append(
                    {
                        "type": "mobile",
                        "question_number": mp.page_number,
                        "img_pk": mp.image.pk,
                    }
                )
        for paper in no_fixed_but_some_mobile:
            complete[paper.paper_number] = []
            for mp in paper.mobilepage_set.all().order_by("question_number"):
                complete[paper.paper_number].append(
                    {
                        "type": "mobile",
                        "question_number": mp.question_number,
                        "img_pk": mp.image.pk,
                    }
                )
        return complete

    @transaction.atomic
    def get_number_incomplete_test_papers(self):
        """
        Return the number of test-papers that are not completely scanned.

        A paper is not completely scanned when it has *some* but not all its fixed pages.
        """

        # Get fixed pages with no image - ie not scanned.
        fixed_with_no_scan = FixedPage.objects.filter(paper=OuterRef("pk"), image=None)
        # Get fixed pages with image - ie scanned.
        fixed_with_scan = FixedPage.objects.filter(
            paper=OuterRef("pk"), image__isnull=False
        )
        # Get count of papers with some but not all scanned fixed pages
        some_but_not_all_fixed_present = Paper.objects.filter(
            Exists(fixed_with_no_scan), Exists(fixed_with_scan)
        )

        return some_but_not_all_fixed_present.count()

    @transaction.atomic
    def get_number_unused_test_papers(self):
        """
        Return the number of test-papers that are usused.

        A paper is unused when it has no fixed page images nor any mobile pages.
        """

        # Get fixed pages with image - ie scanned.
        fixed_with_scan = FixedPage.objects.filter(
            paper=OuterRef("pk"), image__isnull=False
        )
        # get mobile pages
        mobile_pages = MobilePage.objects.filter(paper=OuterRef("pk"))
        # Get count of papers with neither fixed-with-scan nor mobile-pages
        no_images_at_all = Paper.objects.filter(
            ~Exists(fixed_with_scan), ~Exists(mobile_pages)
        )

        return no_images_at_all.count()

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
            page_query = FixedPage.objects.filter(paper=tp).order_by("page_number")
            is_incomplete = page_query.filter(image=None).exists()

            if (is_incomplete and not exclude_incomplete) or (
                not is_incomplete and not exclude_complete
            ):
                pages = []
                for p in page_query:
                    pages.append(
                        {
                            "image": p.image,
                            "version": p.version,
                            "number": p.page_number,
                        }
                    )

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
        page = FixedPage.objects.get(paper=paper, page_number=index)
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

        root_folder = settings.MEDIA_ROOT / "page_images" / "discarded_pages"
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
        image_path = self.get_discarded_image_path(
            colliding_image.hash, make_dirs=make_dirs
        )

        discarded_image = DiscardedImage(
            bundle=colliding_image.bundle,
            bundle_order=colliding_image.bundle_order,
            original_name=colliding_image.original_name,
            file_name=str(image_path),
            hash=colliding_image.hash,
            rotation=colliding_image.rotation,
            restore_class="Colliding page",
            restore_fields={
                "paper_number": colliding_image.paper_number,
                "page_number": colliding_image.page_number,
            },
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
            restore_class="Colliding page",
            restore_fields={
                "paper_number": colliding_image.paper_number,
                "page_number": colliding_image.page_number,
            },
        )

        new_image = Image(
            bundle=colliding_image.bundle,
            bundle_order=colliding_image.bundle_order,
            original_name=colliding_image.original_name,
            file_name=image.file_name,
            hash=colliding_image.hash,
            rotation=colliding_image.rotation,
        )

        image_page = FixedPage.objects.get(image=image)
        image_page.image = new_image

        staged_image = StagingImage.objects.get(
            bundle__pdf_hash=colliding_image.bundle.hash,
            bundle_order=colliding_image.bundle_order,
        )
        staged_image.colliding = False
        staged_image.save()

        if make_dirs:
            shutil.move(str(image.file_name), str(discarded_page.file_name))
            shutil.move(str(colliding_image.file_name), str(new_image.file_name))

        colliding_image.delete()
        image.delete()
        discarded_page.save()
        new_image.save()
        image_page.save()

    @transaction.atomic
    def restore_colliding_image(self, discarded_image, make_dirs=True):
        """
        Undo the discarding of a colliding image.

        Args:
            discarded_image: reference to a DiscardedImage instance
            make_dirs (optional): bool, set to False for testing
        """
        if "Colliding" not in discarded_image.restore_class:
            raise RuntimeError("Discarded image was not originally a colliding image.")

        colliding_fields = discarded_image.restore_fields

        root_dir = settings.MEDIA_ROOT / "page_images" / "colliding_pages"
        test_paper_dir = root_dir / str(colliding_fields["paper_number"])
        image_path = (
            test_paper_dir
            / f"page{colliding_fields['page_number']}_{discarded_image.hash}.png"
        )

        new_colliding_image = CollidingImage(
            bundle=discarded_image.bundle,
            bundle_order=discarded_image.bundle_order,
            original_name=discarded_image.original_name,
            file_name=str(image_path),
            hash=discarded_image.hash,
            rotation=discarded_image.rotation,
            paper_number=colliding_fields["paper_number"],
            page_number=colliding_fields["page_number"],
        )

        if make_dirs:
            root_dir.mkdir(exist_ok=True)
            test_paper_dir.mkdir(exist_ok=True)
            shutil.move(str(discarded_image.file_name), str(image_path))

        discarded_image.delete()
        new_colliding_image.save()
        return new_colliding_image

    @transaction.atomic
    def get_n_discarded_pages(self):
        """
        Return the number of discarded images.
        """

        discarded = DiscardedImage.objects.all()
        return len(discarded)

    @transaction.atomic
    def get_discarded_pages_list(self):
        """
        Return a list of discarded pages.
        """

        discarded_images = []
        discarded = DiscardedImage.objects.all()

        for image in discarded:
            if "Colliding" in image.restore_class:
                restore_fields = image.restore_fields
                previous_type = f"Collision (paper {restore_fields['paper_number']}, page {restore_fields['page_number']})"

            discarded_images.append(
                {
                    "discarded_hash": image.hash,
                    "previous_type": previous_type,
                }
            )

        return discarded_images

    @transaction.atomic
    def get_discarded_image(self, discarded_hash):
        """
        Get a discarded image from its hash.
        """

        return DiscardedImage.objects.get(hash=discarded_hash)

    @transaction.atomic
    def delete_discarded_image(self, discarded_hash):
        """
        Delete a discarded page-image for good.
        """

        DiscardedImage.objects.get(hash=discarded_hash).delete()

    @transaction.atomic
    def restore_discarded_image(self, discarded_hash, make_dirs=True):
        """
        Restore a discarded page-image.

        Args:
            discarded_hash: str, the image hash
            make_dirs (optional): bool, set to False for testing.
        """

        image = self.get_discarded_image(discarded_hash)
        image_class = image.restore_class

        if "Colliding" in image_class:
            self.restore_colliding_image(image, make_dirs=make_dirs)
        # TODO: calls for unknown images, page images, error images, etc
        else:
            raise ValueError("Unable to determine original class of discarded image.")

    @transaction.atomic
    def get_error_pages_list(self):
        """
        Return a list of error pages.
        """

        error_pages = []
        all_error_pages = ErrorImage.objects.filter(flagged=True)

        for error_page in all_error_pages:
            test_paper = error_page.paper_number
            page_number = error_page.page_number
            version_number = error_page.version_number
            file_name = str(test_paper).zfill(5) + str(page_number).zfill(3) + ".png"
            if error_page.comment:
                error_comment = error_page.comment.split("::")
                flagged_by = error_comment[0].lower()
                scanner_comment = error_comment[1]
            else:
                flagged_by = None
                scanner_comment = None
            error_img_hash = str(error_page.hash)

            error_pages.append(
                {
                    "test_paper": test_paper,
                    "page_number": page_number,
                    "version": version_number,
                    "file_name": file_name,
                    "flagged": flagged_by,
                    "comment": scanner_comment,
                    "error_hash": error_img_hash,
                }
            )
        return error_pages

    @transaction.atomic
    def get_error_image(self, error_image_hash):
        """
        Return an error image object based on the hash.

        Args:
            error_image_hash: sha 256 of the image.
        """
        return ErrorImage.objects.get(hash=error_image_hash)

    @transaction.atomic
    def get_n_error_image(self):
        """
        Return number of error pages that are flagged
        to the manager.
        """
        return len(ErrorImage.objects.filter(flagged=True))

    @transaction.atomic
    def get_n_bundles(self):
        """
        Return the number of uploaded bundles.
        """

        return len(StagingBundle.objects.all())

    @transaction.atomic
    def get_bundles_list(self):
        """
        Return a list of all uploaded bundles.
        """

        bundles = StagingBundle.objects.all()

        bundle_list = []
        for bundle in bundles:
            n_pages = len(StagingImage.objects.filter(bundle=bundle))
            n_complete = len(Image.objects.filter(bundle__hash=bundle.pdf_hash))
            time_uploaded = timezone.make_aware(
                datetime.fromtimestamp(bundle.timestamp)
            )

            bundle_list.append(
                {
                    "name": bundle.slug,
                    "username": bundle.user.username,
                    "uploaded": arrow.get(time_uploaded).humanize(),
                    "n_pages": n_pages,
                    "n_complete": n_complete,
                }
            )

        return bundle_list

    @transaction.atomic
    def get_pushed_image(self, img_pk):
        try:
            img = Image.objects.get(pk=img_pk)
            return img.file_name
        except Image.DoesNotExist:
            return None
