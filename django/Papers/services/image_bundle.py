# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2022-2023 Brennen Chiu
# Copyright (C) 2023 Andrew Rechnitzer

import shutil

from plom.tpv_utils import encodePaperPageVersion

from django.db import transaction
from django.conf import settings
from django_huey import db_task

from Scan.models import (
    StagingImage,
)

from Papers.models import (
    Bundle,
    Image,
    DImage,
    CreateImageTask,
    CollidingImage,
    FixedPage,
    MobilePage,
    QuestionPage,
    Paper,
)
from .paper_creator import PaperCreatorService
from .paper_info import PaperInfoService
from .validated_spec_service import SpecificationService


class ImageBundleService:
    """
    Class to encapsulate all functions around validated page images and bundles.
    """

    def create_bundle(self, name, hash):
        """
        Create a bundle and store its name and sha256 hash.
        """
        if Bundle.objects.filter(hash=hash).exists():
            raise RuntimeError("A bundle with that hash already exists.")
        bundle = Bundle(name=name, hash=hash)
        bundle.save()
        return bundle

    def get_bundle(self, hash):
        """
        Get a bundle from its hash.
        """
        return Bundle.objects.get(hash=hash)

    def get_or_create_bundle(self, name, hash):
        """
        Get a Bundle instance, or create if it doesn't exist
        """

        if not Bundle.objects.filter(hash=hash).exists():
            return self.create_bundle(name, hash)
        else:
            return self.get_bundle(hash)

    def create_image(
        self, bundle, bundle_order, original_name, file_name, hash, rotation
    ):
        """
        Create an image.
        """

        if Image.objects.filter(hash=hash).exists():
            raise RuntimeError("An image with that hash already exists.")
        image = Image(
            bundle=bundle,
            bundle_order=bundle_order,
            original_name=original_name,
            file_name=file_name,
            hash=hash,
            rotation=rotation,
        )
        image.save()
        return image

    def push_staged_image(self, staged_image, test_paper, page_number):
        """
        Save a staged bundle image to the database, after it has been
        successfully validated.

        Args:
            staged_image: StagingImage instance
            test_paper: string, test-paper ID of the image
            page_number: int, page number in the test (not the bundle)
        """
        push_task = self._push_staged_image(staged_image, test_paper, page_number)
        push_obj = CreateImageTask(
            huey_id=push_task.id, staging_image=staged_image, status="queued"
        )
        push_obj.save()

    def create_colliding_image(
        self, staged_image, test_paper, page_number, make_dirs=True
    ):
        """
        Save a colliding image to the database.

        Args:
            staged_image: StagingImage instance
            test_paper: int, test-paper ID of the image
            page_number: int, page number in the test (not the bundle)
            make_dirs (optional): bool, set to False for testing
        """

        if Image.objects.filter(hash=hash).exists():
            raise RuntimeError("An image with that hash already exists.")

        root_folder = settings.MEDIA_ROOT / "page_images" / "colliding_pages"
        test_folder = root_folder / str(test_paper)
        image_path = test_folder / f"page{page_number}_{staged_image.image_hash}.png"

        staged_bundle = staged_image.bundle
        bundle = self.get_or_create_bundle(staged_bundle.slug, staged_bundle.pdf_hash)

        colliding_image = CollidingImage(
            bundle=bundle,
            bundle_order=staged_image.bundle_order,
            original_name=staged_image.file_name,
            file_name=str(image_path),
            hash=staged_image.image_hash,
            rotation=staged_image.rotation,
            paper_number=test_paper,
            page_number=page_number,
        )
        colliding_image.save()

        if make_dirs:
            root_folder.mkdir(exist_ok=True)
            test_folder.mkdir(exist_ok=True)
            shutil.copy(staged_image.file_path, image_path)

    # wrapper in the atomic
    @db_task(queue="tasks")
    def _push_staged_image(staged_image, test_paper, page_number, make_dirs=True):
        """
        Save a staged bundle image to the database, after it has been
        successfully validated.

        Args:
            staged_image: StagingImage instance
            test_paper: int, test-paper ID of the image
            page_number: int, page number in the test (not the bundle)
            make_dirs (optional): bool, set to False for testing (otherwise, creates directories in the file system.)
        """

        image_bundle = ImageBundleService()
        papers = PaperCreatorService()
        info = PaperInfoService()

        if not info.is_this_paper_in_database(test_paper):
            raise RuntimeError(f"Test paper {test_paper} is not in the database.")

        if image_bundle.image_exists(staged_image.image_hash):
            raise RuntimeError("Page image already exists in the database.")

        if info.page_has_image(test_paper, page_number):
            image_bundle.create_colliding_image(
                staged_image, test_paper, page_number, make_dirs=make_dirs
            )
            staged_image.colliding = True
            staged_image.save()
            raise RuntimeError(
                f"Collision page detected: test {test_paper} already has page {page_number}."
            )

        staged_bundle = staged_image.bundle
        bundle = image_bundle.get_or_create_bundle(
            staged_bundle.slug, staged_bundle.pdf_hash
        )

        file_path = image_bundle.get_page_image_path(
            test_paper, f"page{page_number}.png", make_dirs
        )

        image = image_bundle.create_image(
            bundle=bundle,
            bundle_order=staged_image.bundle_order,
            original_name=staged_image.file_name,
            file_name=file_path,
            hash=staged_image.image_hash,
            rotation=staged_image.rotation,
        )

        if make_dirs:
            shutil.copy(staged_image.file_path, file_path)
        staged_image.pushed = True
        staged_image.save()

        papers.update_page_image(test_paper, page_number, image)

    def get_page_image_path(self, test_paper, file_name, make_dirs=True):
        """
        Return a save path for a test-paper page image.
        Also, create the necessary folders in the media directory
        if they don't exist.
        """
        page_image_dir = settings.MEDIA_ROOT / "page_images"
        test_papers_dir = page_image_dir / "test_papers"
        paper_dir = test_papers_dir / str(test_paper)

        if make_dirs:
            page_image_dir.mkdir(exist_ok=True)
            test_papers_dir.mkdir(exist_ok=True)
            paper_dir.mkdir(exist_ok=True)

        return str(paper_dir / file_name)

    def image_exists(self, hash):
        """
        Return True if a page image with the input hash exists in the database.
        """
        return Image.objects.filter(hash=hash).exists()

    @transaction.atomic
    def get_image_pushing_status(self, staged_image):
        """
        Return the status of a staged image's associated CreateImageTask instance
        """
        try:
            task_obj = CreateImageTask.objects.get(staging_image=staged_image)
            return task_obj.status
        except CreateImageTask.DoesNotExist:
            return None

    @transaction.atomic
    def get_image_pushing_message(self, staged_image):
        """
        Return the error message of a staged image's CreateImageTask instance
        """
        try:
            task_obj = CreateImageTask.objects.get(staging_image=staged_image)
            return task_obj.message
        except CreateImageTask.DoesNotExist:
            return None

    @transaction.atomic
    def is_image_pushing_in_progress(self, completed_images):
        """
        Return True if at least one CreateImageTask for a bundle has the status 'queued'
        or 'running'.
        """
        for img in completed_images:
            status = self.get_image_pushing_status(img)
            if status == "queued" or status == "running":
                return True
        return False

    def upload_valid_bundle(self, staged_bundle):
        """
        Assuming all of the pages in the bundle are valid (i.e. have a valid page number,
        paper number, and don't collide with any currently uploaded pages) upload all the pages
        using bulk ORM calls.

        1. Check that all the staging images have page numbers and test numbers
        2. Check that no staging images collide with each other
        3. Check that no staging images collide with any uploaded images
        4. Bulk-create images
        """

        bundle_images = StagingImage.objects.filter(bundle=staged_bundle)

        # Staging has checked this - but we check again here to be very sure
        if not self.all_staged_imgs_valid(bundle_images):
            raise RuntimeError("Some pages in this bundle do not have QR data.")

        # Staging has checked this - but we check again here to be very sure
        collide = self.find_internal_collisions(bundle_images)
        if len(collide) > 0:
            raise RuntimeError(f"Some pages in the staged bundle collide - {collide}")

        # Staging has not checked this - we need to do it here
        collide = self.find_external_collisions(bundle_images)
        if len(collide) > 0:
            raise RuntimeError(
                f"Some pages in the staged bundle collide with uploaded pages - {collide}"
            )

        uploaded_bundle = Bundle(name=staged_bundle.slug, hash=staged_bundle.pdf_hash)
        uploaded_bundle.save()

        # TODO - needs to handle extra pages too.
        for staged in bundle_images:
            image = Image(
                bundle=uploaded_bundle,
                bundle_order=staged.bundle_order,
                original_name=staged.file_name,
                file_name=staged.file_path,
                hash=staged.image_hash,
                rotation=staged.rotation,
            )
            image.save()

            if staged.image_type=="known":           
                known = staged.knownstagingimage
                # TODO - update this for the "type" of each page
                # ID, DNM or question.
                page = FixedPage.objects.get(
                    paper__paper_number=known.paper_number,
                    page_number=known.page_number,
                )
                page.image = image
                page.save(update_fields=["image"])
            elif staged.image_type=="extra":
                # need to make one mobile page for each question in the question-list
                extra = staged.extrastagingimage
                paper = Paper.objects.get(paper_number=extra.paper_number)
                for q in extra.question_list:
                    # TODO presently hard code version to 1 - need to fix
                    MobilePage.objects.create(paper=paper, image=image,question_number=q, version=1)
            elif staged.image_type=="discard":
                disc = staged.discardstagingimage
                DImage.objects.create(image=image, discard_reason = disc.discard_reason)
            else:
                raise ValueError(f"Pushed images must be known, extra or discards - found {staged.image_type}")

        from Mark.services import MarkingTaskService

        mts = MarkingTaskService()
        questions = self.get_ready_questions(uploaded_bundle)
        for paper, question in questions["ready"]:
            paper_instance = Paper.objects.get(paper_number=paper)
            mts.create_task(paper_instance, question)

    def get_staged_img_location(self, staged_image):
        """
        Get the image's paper number and page number from its QR code dict
        TODO: this same thing is implemented in ScanService. We need to choose which one stays!

        Args:
            staged_image: A StagingImage instance

        Returns:
            (int or None, int or None): paper number and page number
        """

        if not staged_image.parsed_qr:
            return (None, None)

        # The values are the same in all of the child QR dicts, so it's safe to choose any
        any_qr = list(staged_image.parsed_qr.values())[0]
        paper_number = any_qr["paper_id"]
        page_number = any_qr["page_num"]

        return paper_number, page_number

    @transaction.atomic
    def all_staged_imgs_valid(self, staged_imgs):
        """Check that all staged images in the bundle are ready to be
        uploaded. Each image must be "known" or "discard" or be
        "extra" with data. There can be no "unknown", "unread",
        "error" or "extra"-without-data.

        Args:
            staged_imgs: QuerySet, a list of all staged images for a bundle

        Returns:
            bool: True if all images are valid, false otherwise

        """
        # while this is done by staging, we redo it here to be **very** sure.
        if staged_imgs.filter(image_type__in=["unread", "unknown", "error"]).exists():
            return False
        if staged_imgs.filter(image_type="extra", extrastagingimage__paper_number__isnull=True).exists():
            return False
        # to do the complement of this search we'd need to count
        # knowns, discards and extra-with-data and make sure that
        # total matches number of pages in the bundle.
        return True

    @transaction.atomic
    def find_internal_collisions(self, staged_imgs):
        """Check for collisions *within* a bundle

        Args:
            staged_imgs: QuerySet, a list of all staged images for a bundle

        Returns:
            list [[StagingImage1.pk, StagingImage2.pk, StagingImage3.pk]]: list
                of unordered collisions so that in each sub-list each image (as
                determined by its primary key) collides with others in that sub-list.
        """

        known_imgs = {}  # dict of short-tpv to list of known-images with that tpv
        # if that list is 2 or more then that it is an internal collision.
        collisions = []

        # note - only known-images will create collisions.
        # extra pages and discards will never collide.
        for image in staged_imgs.filter(image_type="known"):
            knw = image.knownstagingimage
            tpv = encodePaperPageVersion(knw.paper_number, knw.page_number, knw.version)
            # append this image.primary-key to the list of images with that tpv
            known_imgs.setdefault(tpv, []).append(image.pk)
        for tpv, image_list in known_imgs.items():
            if len(image_list) == 1:  # no collision at this tpv
                continue
            collisions.append(image_list)

        return collisions

    @transaction.atomic
    def find_external_collisions(self, staged_imgs):
        """
        Check for collisions between images in the input list and all the
        *currently uploaded* images.

        Args:
            staged_imgs: QuerySet, a list of all staged images for a bundle

        Returns:
            list [(StagingImage, Image)]: list of unordered collisions.
        """

        collisions = []
        # note that only known images can cause collisions
        for image in staged_imgs.filter(image_type="known"):
            known = image.knownstagingimage
            colls = Image.objects.filter(
                fixedpage__paper__paper_number=known.paper_number,
                fixedpage__page_number=known.page_number,
            )
            for colliding_img in colls:
                collisions.append(
                    (image, colliding_img, known.paper_number, known.page_number)
                )
        return collisions

    @transaction.atomic
    def get_ready_questions(self, bundle):
        """
        Find questions across all test-papers in the database that now have
        all of their page-images scanned. These questions are ready to be marked.
        Note: tasks are created on a per-question basis, so a test paper across multiple bundles
        could have some "ready" and "unready" questions.
        TODO: Extra pages could potentially make questions un-ready again.

        Args:
            bundle: a Bundle instance that has just been uploaded.

        Returns:
            dict {}: Two lists of (int, int). "ready" is the list of paper_number/question_number pairs
            that have pages in this bundle, and are now ready to be marked. "not_ready" are
            paper_number/question_number pairs that have pages in this bundle, but are not ready to be
            marked yet.
        """

        question_pages = QuestionPage.objects.filter(image__bundle=bundle)
        papers_in_bundle = question_pages.values_list(
            "paper__paper_number", "question_number"
        )
        bundle_paper_status = set(papers_in_bundle)

        result = {"ready": [], "not_ready": []}

        for paper, question_num in bundle_paper_status:
            n_pushed_pages = (
                QuestionPage.objects.exclude(image__isnull=True)
                .filter(paper__paper_number=paper, question_number=question_num)
                .count()
            )
            n_pages = SpecificationService().n_pages_for_question(question_num)

            if n_pages == n_pushed_pages:
                result["ready"].append((paper, question_num))
            else:
                result["not_ready"].append((paper, question_num))

        return result
