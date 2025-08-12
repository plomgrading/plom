# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2022-2023 Brennen Chiu
# Copyright (C) 2023-2025 Andrew Rechnitzer
# Copyright (C) 2023 Natalie Balashov
# Copyright (C) 2023 Julian Lapenna
# Copyright (C) 2024-2025 Colin B. Macdonald
# Copyright (C) 2025 Aidan Murphy

import pathlib
import uuid
from collections import defaultdict

from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.db.models import QuerySet, Count, Q, OuterRef, Exists

from plom.tpv_utils import encodePaperPageVersion
from plom.plom_exceptions import PlomPushCollisionException
from plom.misc_utils import format_int_list_with_runs
from plom_server.Scan.models import StagingImage, StagingBundle
from plom_server.Preparation.services import PapersPrinted
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
from . import SpecificationService


class ImageBundleService:
    """Class to encapsulate all functions around validated page images and bundles."""

    def create_bundle(self, name: str, pdf_hash: str) -> Bundle:
        """Create a bundle and store its name and sha256 hash."""
        if Bundle.objects.filter(pdf_hash=pdf_hash).exists():
            raise RuntimeError("A bundle with that hash already exists.")
        bundle = Bundle.objects.create(name=name, pdf_hash=pdf_hash)
        return bundle

    def get_bundle(self, pdf_hash: str) -> Bundle:
        """Get a bundle from its hash."""
        return Bundle.objects.get(pdf_hash=pdf_hash)

    def get_or_create_bundle(self, name: str, pdf_hash: str) -> Bundle:
        """Get a Bundle instance, or create if it doesn't exist."""
        if not Bundle.objects.filter(pdf_hash=pdf_hash).exists():
            return self.create_bundle(name, pdf_hash)
        else:
            return self.get_bundle(pdf_hash)

    def image_exists(self, imghash: str) -> bool:
        """Return True if a page image with the input hash exists in the database."""
        return Image.objects.filter(hash=imghash).exists()

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
        1. Check that all the staging images have page numbers and paper numbers
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
            "baseimage",
            "knownstagingimage",
            "extrastagingimage",
            "discardstagingimage",
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
            collide_error_list2 = sorted([X[0].bundle_order for X in collide])
            nicer_list = format_int_list_with_runs(collide_error_list2)
            raise PlomPushCollisionException(
                f"Some images in the staged bundle collide with uploaded pages: {nicer_list}"
            )

        uploaded_bundle = Bundle(
            name=staged_bundle.slug,
            pdf_hash=staged_bundle.pdf_hash,
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
                for q in extra.question_idx_list:
                    prefix += f"{q}_"
                # otherwise if no question index use dnm
                if not extra.question_idx_list:
                    prefix += "dnm_"
            elif staged.image_type == StagingImage.DISCARD:
                prefix = "discard_"
            else:
                prefix = ""

            suffix = pathlib.Path(staged.baseimage.image_file.name).suffix
            return prefix + str(uuid.uuid4()) + suffix

        # we create all the images as O(n) but then update
        # fixed-pages and associated structures in O(1) - I hope
        new_mobile_pages = []
        new_discard_pages = []
        updated_fixed_pages = []
        # we need all the fixed pages that are touched by these new images
        # to get that we find all the papers that are touched and
        # then get **all** the fixed pages from those papers.
        paper_numbers = set(
            staged.knownstagingimage.paper_number
            for staged in bundle_images
            if staged.image_type == StagingImage.KNOWN
        )
        # make look-up dict to more-easily get fixed pages from (papernum, pagenum)
        # note that a given pn/page may have multiple fixed pages (e.g., when
        # questions share pages).
        fixedpage_by_pn_pg = defaultdict(list)
        for fp in (
            FixedPage.objects.select_for_update()
            .filter(paper__paper_number__in=paper_numbers)
            .prefetch_related("paper")
        ):
            fixedpage_by_pn_pg[(fp.paper.paper_number, fp.page_number)].append(fp)

        for staged in bundle_images:
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
                original_name=staged.baseimage.image_file.name,
                baseimage=staged.baseimage,
                rotation=rot_to_push,
                parsed_qr=staged.parsed_qr,
            )
            image.save()

            if staged.image_type == StagingImage.KNOWN:
                known = staged.knownstagingimage
                # Note that since fixedpage is polymorphic, this will handle question, ID and DNM pages.
                fp_list = fixedpage_by_pn_pg[(known.paper_number, known.page_number)]
                if len(fp_list) == 0:
                    raise ObjectDoesNotExist(
                        f"Paper {known.paper_number}"
                        f" page {known.page_number} does not exist"
                    )
                for fp in fp_list:
                    fp.image = image
                    updated_fixed_pages.append(fp)

            elif staged.image_type == StagingImage.EXTRA:
                # need to make one mobile page for each question in the question-list
                extra = staged.extrastagingimage
                paper = Paper.objects.get(paper_number=extra.paper_number)
                for q in extra.question_idx_list:
                    # get the version from the paper/question info
                    v = pi_service.get_version_from_paper_question(
                        extra.paper_number, q
                    )
                    # defer actual DB creation to bulk operation later
                    new_mobile_pages.append(
                        MobilePage(
                            paper=paper, image=image, question_index=q, version=v
                        )
                    )
                # otherwise, if question index list empty, make a non-marked MobilePage
                if not extra.question_idx_list:
                    new_mobile_pages.append(
                        MobilePage(
                            paper=paper,
                            image=image,
                            question_index=MobilePage.DNM_qidx,
                            version=0,
                        )
                    )
            elif staged.image_type == StagingImage.DISCARD:
                disc = staged.discardstagingimage
                new_discard_pages.append(
                    DiscardPage(image=image, discard_reason=disc.discard_reason)
                )
            else:
                raise ValueError(
                    f"Pushed images must be known, extra or discards - found {staged.image_type}"
                )
        MobilePage.objects.bulk_create(new_mobile_pages)
        DiscardPage.objects.bulk_create(new_discard_pages)
        FixedPage.objects.bulk_update(updated_fixed_pages, ["image"])

        from plom_server.Mark.services import MarkingTaskService
        from plom_server.Identify.services import IdentifyTaskService
        from plom_server.Identify.services import IDReaderService

        # bulk create the associated marking tasks in O(1)
        ready = self._get_ready_questions_in_bundle(uploaded_bundle)
        MarkingTaskService.bulk_create_and_update_marking_tasks(ready)

        # bulk create the associated ID tasks in O(1).
        papers = [
            id_page.paper for id_page in self.get_id_pages_in_bundle(uploaded_bundle)
        ]
        IdentifyTaskService.bulk_create_id_tasks(papers)
        # now create any prename-predictions
        IDReaderService.bulk_add_or_update_prename_ID_predictions(user_obj, papers)

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
        for image in staged_imgs.filter(image_type=StagingImage.KNOWN).prefetch_related(
            "knownstagingimage"
        ):
            knw = image.knownstagingimage
            tpv = encodePaperPageVersion(knw.paper_number, knw.page_number, knw.version)
            # append this image.primary-key to the list of images with that tpv
            known_imgs.setdefault(tpv, []).append(image.pk)
        for tpv, image_list in known_imgs.items():
            if len(image_list) == 1:  # no collision at this tpv
                continue
            collisions.append(image_list)

        return collisions

    @staticmethod
    @transaction.atomic
    def find_external_collisions(
        staged_imgs: QuerySet,
    ) -> list[tuple[StagingImage, Image, int, int]]:
        """Check for collisions between images in the input list and all the *currently uploaded* images.

        Args:
            staged_imgs: QuerySet, a list of all staged images for a bundle

        Returns:
            An unordered collection of tuples of describing collisions.
        """
        # note that only known images can cause collisions
        # get all the known paper/pages in the bundle
        staged_pp_img_dict = {
            (img.knownstagingimage.paper_number, img.knownstagingimage.page_number): img
            for img in staged_imgs.filter(image_type=StagingImage.KNOWN)
        }
        # get the list of papers in the bundle so that we can grab all
        # known pages from just those papers.
        staged_paper_nums = [pp[0] for pp in staged_pp_img_dict.keys()]
        pushed_img_pp_dict = {
            (X.paper.paper_number, X.page_number): X.image
            for X in FixedPage.objects.filter(
                image__isnull=False, paper__paper_number__in=staged_paper_nums
            ).prefetch_related("paper", "image")
        }
        # now compare image by image and store list of collisions
        collisions = []
        for pp, img in staged_pp_img_dict.items():
            if pp in pushed_img_pp_dict:
                collisions.append((img, pushed_img_pp_dict[pp], pp[0], pp[1]))
        return collisions

    @staticmethod
    @transaction.atomic
    def _get_ready_questions_in_bundle(bundle: Bundle) -> list[tuple[int, int, int]]:
        """Find ready questions across all papers affected by this bundle.

        A question is ready when either it has all of its
        fixed-pages, or it has no fixed-pages but has some
        mobile-pages.

        Note: at any given time a paper could have some "ready" and "unready" questions.

        Args:
            bundle: a Bundle instance.

        Returns:
            A list containing tuples of paper_number, question_index, version,
            for each paper question pair that's 'ready'.
        """
        question_pages = QuestionPage.objects.filter(image__bundle=bundle)
        extras = MobilePage.objects.filter(image__bundle=bundle)

        # version isn't necessary for the readiness check
        # but it can be fetched here with little additional overhead
        # remove duplicates by casting to a set
        papers_questions_versions_updated_by_bundle = set(
            list(
                question_pages.values_list(
                    "paper__paper_number", "question_index", "version"
                )
            )
            + list(
                extras.values_list("paper__paper_number", "question_index", "version")
            )
        )

        # now check if pq pairs are markable
        paper_question_pairs_dict = ImageBundleService().are_paper_question_pairs_ready(
            [t[:2] for t in papers_questions_versions_updated_by_bundle]
        )
        pqv_updated_and_ready = [
            t
            for t in papers_questions_versions_updated_by_bundle
            if paper_question_pairs_dict[t[:2]]
        ]
        return pqv_updated_and_ready

    @transaction.atomic
    def get_id_pages_in_bundle(self, bundle: Bundle) -> QuerySet[IDPage]:
        """Get all of the ID pages in an uploaded bundle, in order to initialize ID tasks.

        Args:
            bundle: a Bundle instance

        Returns:
            A query of only the ID pages in the input bundle
        """
        return IDPage.objects.filter(image__bundle=bundle).prefetch_related("paper")

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
    def _get_ready_paper_question_pairs(self) -> list[tuple[int, int]]:
        """Get all paper question pairs that are ready for marking.

        This function queries database images directly to determine
        if a given paper has enough work submitted to be marked.
        It does **not** check if a question has already been marked,
        or if marking is in progress, for that you must query the
        relevant MarkingTask
        To be 'ready' a paper/question pair must either
          * have all its fixed pages with images (and any
            number of mobile pages), or
          * have no fixed pages with images but some mobile pages

        Returns:
            a list of tuples, each containing a paper number and question pair
            TODO: ideally this would return a lazy queryset, but that requires
            a common relation for mobile and question pages (#2871)
        """
        # get all scanned pages (relevant to questions)
        filled_qpages = QuestionPage.objects.filter(image__isnull=False)
        mpages = MobilePage.objects.all()

        # number of pages per question
        test_page_dict = SpecificationService.get_question_pages()
        qidx_spec_page_count = {
            key: len(values) for key, values in test_page_dict.items()
        }

        # case 1 - all fixed pages have images
        filled_qpages_counts = filled_qpages.values(
            "paper__paper_number", "question_index"
        ).annotate(page_count=Count("id"))
        all_pages_filter = Q()
        for qidx, spec_page_count in qidx_spec_page_count.items():
            all_pages_filter |= Q(question_index=qidx, page_count__gte=spec_page_count)

        ready_pairs_1 = (
            filled_qpages_counts.filter(all_pages_filter)
            .values_list("paper__paper_number", "question_index")
            .distinct()
        )

        # case 2 - all fixed pages have no images, but there's mobile pages

        # we are emulating this query:
        # SELECT mp.paper, mp.question_index
        # FROM MobilePage mp LEFT OUTER JOIN QuestionPage_withimage qp
        # ON mp.paper = qp.paper AND mp.question_index = qp.question_index
        subquery = filled_qpages.filter(
            paper=OuterRef("paper"),
            question_index=OuterRef("question_index"),
        )
        mpages_filtered = mpages.annotate(nofixed=~Exists(subquery))

        ready_pairs_2 = (
            mpages_filtered.filter(
                nofixed=True, question_index__in=list(test_page_dict.keys())
            )
            .values_list("paper__paper_number", "question_index")
            .distinct()
        )
        # By design, case 1 and case 2 pairs will never collide
        ready = list(ready_pairs_1) + list(ready_pairs_2)

        return ready

    @transaction.atomic
    def are_paper_question_pairs_ready(
        self, paper_qidx_pairs: list[tuple[int, int]]
    ) -> dict[tuple[int, int], bool]:
        """Check if provided paper/question pairs are ready for marking.

        See :func:`_get_ready_paper_question_pairs` for what 'ready' means.

        Args:
            paper_qidx_pairs: a list of tuples identifying a particular
                question on a particular paper. The tuples should be formatted
                as (paper_number, qidx).

        Returns:
            A dict with the input paper number/qidx tuples as keys, and True/False
            as the values.
        """
        test_questions = list(SpecificationService.get_question_pages().keys())
        ready_pairs = self._get_ready_paper_question_pairs()
        pq_pair_ready = {}
        for pair in paper_qidx_pairs:
            if pair[1] not in test_questions:
                raise ValueError(
                    f"question index '{pair[1]}' doesn't correspond"
                    " to any question on this assessment."
                )
            pq_pair_ready[pair] = pair in ready_pairs
        return pq_pair_ready
