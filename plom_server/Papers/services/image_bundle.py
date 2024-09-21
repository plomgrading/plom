# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2022-2023 Brennen Chiu
# Copyright (C) 2023-2024 Andrew Rechnitzer
# Copyright (C) 2023 Natalie Balashov
# Copyright (C) 2023 Julian Lapenna
# Copyright (C) 2024 Colin B. Macdonald

from __future__ import annotations

import pathlib
import uuid

from plom.tpv_utils import encodePaperPageVersion

from django.contrib.auth.models import User
from django.core.files import File
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.db.models import QuerySet

from Scan.models import StagingImage, StagingBundle

from Preparation.services import PapersPrinted
from ..models import (
    Bundle,
    Image,
    DiscardPage,
    CreateImageHueyTask,
    FixedPage,
    MobilePage,
    QuestionPage,
    IDPage,
    Paper,
)
from .paper_info import PaperInfoService

from plom.plom_exceptions import PlomPushCollisionException
from plom.misc_utils import format_int_list_with_runs


class ImageBundleService:
    """Class to encapsulate all functions around validated page images and bundles."""

    def create_bundle(self, name: str, hash: str) -> Bundle:
        """Create a bundle and store its name and sha256 hash."""
        if Bundle.objects.filter(hash=hash).exists():
            raise RuntimeError("A bundle with that hash already exists.")
        bundle = Bundle.objects.create(name=name, hash=hash)
        return bundle

    def get_bundle(self, hash: str) -> Bundle:
        """Get a bundle from its hash."""
        return Bundle.objects.get(hash=hash)

    def get_or_create_bundle(self, name: str, hash: str) -> Bundle:
        """Get a Bundle instance, or create if it doesn't exist."""
        if not Bundle.objects.filter(hash=hash).exists():
            return self.create_bundle(name, hash)
        else:
            return self.get_bundle(hash)

    def image_exists(self, hash: str) -> bool:
        """Return True if a page image with the input hash exists in the database."""
        return Image.objects.filter(hash=hash).exists()

    @transaction.atomic
    def get_image_pushing_status(self, staged_image: StagingImage) -> str | None:
        """Return the status of a staged image's associated CreateImageHueyTask instance."""
        try:
            task_obj = CreateImageHueyTask.objects.get(staging_image=staged_image)
            return task_obj.status
        except CreateImageHueyTask.DoesNotExist:
            return None

    @transaction.atomic
    def get_image_pushing_message(self, staged_image: StagingImage) -> str | None:
        """Return the error message of a staged image's CreateImageHueyTask instance."""
        try:
            task_obj = CreateImageHueyTask.objects.get(staging_image=staged_image)
            return task_obj.message
        except CreateImageHueyTask.DoesNotExist:
            return None

    @transaction.atomic
    def is_image_pushing_in_progress(self, completed_images) -> bool:
        """Return True if at least one CreateImageHueyTask for a bundle has the status 'queued' or 'running'."""
        for img in completed_images:
            status = self.get_image_pushing_status(img)
            if status == "queued" or status == "running":
                return True
        return False

    def upload_valid_bundle(self, staged_bundle: StagingBundle, user_obj: User) -> None:
        """Upload all the pages using bulk calls under certain assumptions.

        Assuming all of the pages in the bundle are valid (i.e. have a valid page number,
        paper number, and don't collide with any currently uploaded pages) upload all the pages
        using bulk ORM calls.

        0. Check that preparation has been finished
        1. Check that all the staging images have page numbers and test numbers
        2. Check that no staging images collide with each other
        3. Check that no staging images collide with any uploaded images
        4. Bulk-create images

        Raises:
            RuntimeError
            PlomPushCollisionException
            ValueError
            ObjectDoesNotExist
        """
        if not PapersPrinted.have_papers_been_printed():
            raise RuntimeError("Papers have not yet been printed.")

        bundle_images = StagingImage.objects.filter(
            bundle=staged_bundle
        ).prefetch_related(
            "knownstagingimage", "extrastagingimage", "discardstagingimage"
        )

        # Staging has checked this - but we check again here to be very sure
        if not self.all_staged_imgs_valid(bundle_images):
            raise RuntimeError("Some pages in this bundle do not have QR data.")

        # Staging has checked this - but we check again here to be very sure
        collide = self.find_internal_collisions(bundle_images)
        if len(collide) > 0:
            # just make a list of bundle-orders of the colliding images
            collide_error_list = [[Y.bundle_order for Y in X] for X in collide]
            raise PlomPushCollisionException(
                f"Some images within the staged bundle collide with each-other: {collide_error_list}"
            )

        # Staging has not checked this - we need to do it here
        collide = self.find_external_collisions(bundle_images)
        if len(collide) > 0:
            # just make a list of bundle-orders of the colliding images
            collide_error_list = sorted([X[0].bundle_order for X in collide])
            nicer_list = format_int_list_with_runs(collide_error_list)
            raise PlomPushCollisionException(
                f"Some images in the staged bundle collide with uploaded pages: {nicer_list}"
            )

        uploaded_bundle = Bundle(
            name=staged_bundle.slug,
            hash=staged_bundle.pdf_hash,
            user=user_obj,
            staging_bundle=staged_bundle,
        )
        uploaded_bundle.save()

        pi_service = PaperInfoService()

        def image_save_name(staged) -> str:
            if staged.image_type == StagingImage.KNOWN:
                known = staged.knownstagingimage
                prefix = f"known_{known.paper_number}_{known.page_number}_"
            elif staged.image_type == StagingImage.EXTRA:
                extra = staged.extrastagingimage
                prefix = f"extra_{extra.paper_number}_"
                for q in extra.question_list:
                    prefix += f"{q}_"
            elif staged.image_type == StagingImage.DISCARD:
                prefix = "discard_"
            else:
                prefix = ""

            suffix = pathlib.Path(staged.image_file.name).suffix
            return prefix + str(uuid.uuid4()) + suffix

        for staged in bundle_images:
            with staged.image_file.open("rb") as fh:
                # ensure that a pushed image has a defined rotation
                # hard-coded to set rotation=0 if no staging image rotation exists
                # the use of rotation=None for StagingImages is currently unused,
                # but could be in future for user scanning orientation default: see #1825 and #2050
                if staged.rotation is None:
                    rot_to_push = 0
                else:
                    rot_to_push = staged.rotation
                image = Image(
                    bundle=uploaded_bundle,
                    bundle_order=staged.bundle_order,
                    original_name=staged.image_file.name,
                    image_file=File(fh, name=image_save_name(staged)),
                    hash=staged.image_hash,
                    rotation=rot_to_push,
                    parsed_qr=staged.parsed_qr,
                )
                image.save()

            if staged.image_type == StagingImage.KNOWN:
                known = staged.knownstagingimage
                # Note that since fixedpage is polymorphic, this will handle question, ID and DNM pages.
                pages = FixedPage.objects.filter(
                    paper__paper_number=known.paper_number,
                    page_number=known.page_number,
                ).select_for_update()
                if not pages:
                    raise ObjectDoesNotExist(
                        f"Paper {known.paper_number}"
                        f" page {known.page_number} does not exist"
                    )
                # Can be more than one FixedPage when questions share pages
                for page in pages:
                    page.image = image
                    page.save(update_fields=["image"])
            elif staged.image_type == StagingImage.EXTRA:
                # need to make one mobile page for each question in the question-list
                extra = staged.extrastagingimage
                paper = Paper.objects.get(paper_number=extra.paper_number)
                for q in extra.question_list:
                    # get the version from the paper/question info
                    v = pi_service.get_version_from_paper_question(
                        extra.paper_number, q
                    )
                    MobilePage.objects.create(
                        paper=paper, image=image, question_index=q, version=v
                    )
            elif staged.image_type == StagingImage.DISCARD:
                disc = staged.discardstagingimage
                DiscardPage.objects.create(
                    image=image, discard_reason=disc.discard_reason
                )
            else:
                raise ValueError(
                    f"Pushed images must be known, extra or discards - found {staged.image_type}"
                )

        from Mark.services import MarkingTaskService
        from Identify.services import IdentifyTaskService
        from Identify.services import IDReaderService
        from Preparation.services import StagingStudentService

        mts = MarkingTaskService()
        its = IdentifyTaskService()
        questions = self.get_ready_questions(uploaded_bundle)
        for paper, question in questions["ready"]:
            paper_instance = Paper.objects.get(paper_number=paper)
            mts.create_task(paper_instance, question)

        for id_page in self.get_id_pages_in_bundle(uploaded_bundle):
            paper = id_page.paper
            if not its.id_task_exists(paper):
                its.create_task(paper)

                # instantiate prename predictions
                student_service = StagingStudentService()
                prename_sid = student_service.get_prename_for_paper(paper.paper_number)
                if prename_sid:
                    id_reader_service = IDReaderService()
                    id_reader_service.add_prename_ID_prediction(
                        user_obj, prename_sid, paper.paper_number
                    )

    def get_staged_img_location(
        self, staged_image: StagingImage
    ) -> tuple[int | None, int | None]:
        """Get the image's paper number and page number from its QR code dict.

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
    def all_staged_imgs_valid(self, staged_imgs: QuerySet) -> bool:
        """Check that all staged images in the bundle are ready to be uploaded.

        Each image must be "known" or "discard" or be
        "extra" with data. There can be no "unknown", "unread",
        "error" or "extra"-without-data.

        Args:
            staged_imgs: QuerySet, a list of all staged images for a bundle

        Returns:
            True if all images are valid, False otherwise.
        """
        # while this is done by staging, we redo it here to be **very** sure.
        if staged_imgs.filter(
            image_type__in=[
                StagingImage.UNREAD,
                StagingImage.UNKNOWN,
                StagingImage.ERROR,
            ]
        ).exists():
            return False
        if staged_imgs.filter(
            image_type=StagingImage.EXTRA, extrastagingimage__paper_number__isnull=True
        ).exists():
            return False
        # to do the complement of this search we'd need to count
        # knowns, discards and extra-with-data and make sure that
        # total matches number of pages in the bundle.
        return True

    @transaction.atomic
    def find_internal_collisions(
        self, staged_imgs: QuerySet[StagingImage]
    ) -> list[list[int]]:
        """Check for collisions *within* a bundle.

        Args:
            staged_imgs: QuerySet, a list of all staged images for a bundle

        Returns:
            A list of unordered collisions so that in each sub-list each image (as
            determined by its primary key) collides with others in that sub-list.
            Looks something like:
            ``[[StagingImage1.pk, StagingImage2.pk, StagingImage3.pk], ...]``
        """
        # temporary dict of short-tpv to list of known-images with that tpv
        known_imgs: dict[str, list[int]] = {}
        # if that list is 2 or more then that it is an internal collision.
        collisions = []

        # note - only known-images will create collisions.
        # extra pages and discards will never collide.
        for image in staged_imgs.filter(image_type=StagingImage.KNOWN):
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
    def find_external_collisions(self, staged_imgs: QuerySet) -> list:
        """Check for collisions between images in the input list and all the *currently uploaded* images.

        Args:
            staged_imgs: QuerySet, a list of all staged images for a bundle

        Returns:
            list [(StagingImage, Image, paper_number, page_number)]: list of unordered collisions.
        """
        collisions = []
        # note that only known images can cause collisions
        for image in staged_imgs.filter(image_type=StagingImage.KNOWN):
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
    def get_ready_questions(self, bundle: Bundle) -> dict[str, list[tuple[int, int]]]:
        """Find questions across all test-papers in the database that now ready.

        A question is ready when either it has all of its
        fixed-pages, or it has no fixed-pages but has some
        mobile-pages.

        Note: tasks are created on a per-question basis, so a test paper across multiple bundles
        could have some "ready" and "unready" questions.

        Args:
            bundle: a Bundle instance that has just been uploaded.

        Returns:
            Dict with two keys, each to a list of ints.
            "ready" is the list of paper_number/question_index pairs
            that have pages in this bundle, and are now ready to be marked.
            "not_ready" are paper_number/question_index pairs that have pages
            in this bundle, but are not ready to be marked yet.
        """
        # find all question-pages (ie fixed pages) that attach to images in the current bundle.
        question_pages = QuestionPage.objects.filter(image__bundle=bundle)
        # find all mobile pages (extra pages) that attach to images in the current bundle
        extras = MobilePage.objects.filter(image__bundle=bundle)

        # now make list of all papers/questions updated by this bundle
        # note that values_list does not return a list, it returns a "query-set"
        papers_in_bundle = list(
            question_pages.values_list("paper__paper_number", "question_index")
        ) + list(extras.values_list("paper__paper_number", "question_index"))
        # remove duplicates by casting to a set
        papers_questions_updated_by_bundle = set(papers_in_bundle)

        # for each paper/question that has been updated, check if has either
        # all fixed pages, or no fixed pages but some mobile-pages.
        # if some, but not all, fixed pages then is not ready.

        result: dict[str, list[tuple[int, int]]] = {"ready": [], "not_ready": []}

        for paper_number, question_index in papers_questions_updated_by_bundle:
            q_pages = QuestionPage.objects.filter(
                paper__paper_number=paper_number, question_index=question_index
            )
            pages_no_img = q_pages.filter(image__isnull=True).count()
            if pages_no_img == 0:  # all fixed pages have images
                result["ready"].append((paper_number, question_index))
                continue
            # question has some images
            pages_with_img = q_pages.filter(image__isnull=False).count()
            if (
                pages_with_img > 0
            ):  # question has some pages with and some without images - not ready
                result["not_ready"].append((paper_number, question_index))
                continue
            # all fixed pages without images - check if has any mobile pages
            if (
                MobilePage.objects.filter(
                    paper__paper_number=paper_number, question_index=question_index
                ).count()
                > 0
            ):
                result["ready"].append((paper_number, question_index))

        return result

    @transaction.atomic
    def get_id_pages_in_bundle(self, bundle: Bundle) -> QuerySet[IDPage]:
        """Get all of the ID pages in an uploaded bundle, in order to initialize ID tasks.

        Args:
            bundle: a Bundle instance

        Returns:
            A query of only the ID pages in the input bundle
        """
        return IDPage.objects.filter(image__bundle=bundle)

    @transaction.atomic
    def is_given_paper_ready_for_id_ing(self, paper_obj: Paper) -> bool:
        """Check if the id page of the given paper has an image and so is ready for id-ing.

        Args:
            paper_obj (Paper): the database paper to check

        Returns:
            bool: true when paper is ready for id-ing (ie the IDpage has an image)
        """
        return IDPage.objects.filter(paper=paper_obj, image__isnull=False).exists()

    @transaction.atomic
    def is_given_paper_question_ready(
        self, paper_obj: Paper, question_index: int
    ) -> bool:
        """Check if a given paper/question is ready for marking.

        Note that to be ready the question must either
          * have all its fixed pages with images (and any
            number of mobile pages), or
          * have no fixed pages with images but some mobile pages


        Args:
            paper_obj: the database paper object to check.
            question_index: the question to check.

        Returns:
            True when the question of the given paper is ready for marking, false otherwise.

        Raises:
            ValueErrorr when there does not exist any question pages for
                that paper (eg when the question index is out of range).
        """
        q_pages = QuestionPage.objects.filter(
            paper=paper_obj, question_index=question_index
        )
        # todo - this should likely be replaced with a spec check
        if not q_pages.exists():
            raise ValueError(
                f"There are no question_pages at all for paper {paper_obj.paper_number}"
                f"question index {question_index}"
            )

        qp_no_img = q_pages.filter(image__isnull=True).exists()
        qp_with_img = q_pages.filter(image__isnull=False).exists()
        # note that (qp_no_img or qp_with_img == True)
        mp_present = MobilePage.objects.filter(
            paper=paper_obj, question_index=question_index
        ).exists()

        if qp_with_img:
            # there are some fixed pages with images
            if qp_no_img:
                # there are some fixed pages without images, so partially scanned. not ready.
                return False
            else:
                # all fixed question pages have images, so it is ready
                return True
        else:
            # all fixed pages have no images.
            if mp_present:
                # the question has no fixed pages scanned, but does have a mobile page, so ready.
                return True
            else:
                # no images present at all, so not ready
                return False
