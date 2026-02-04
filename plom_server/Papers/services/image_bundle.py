# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2022-2023 Brennen Chiu
# Copyright (C) 2023-2025 Andrew Rechnitzer
# Copyright (C) 2023 Natalie Balashov
# Copyright (C) 2023 Julian Lapenna
# Copyright (C) 2024-2026 Colin B. Macdonald
# Copyright (C) 2025-2026 Aidan Murphy

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
    Paper,
)
from .paper_info import PaperInfoService
from . import SpecificationService


class ImageBundleService:
    """Class to encapsulate functions around validated page images and bundles."""

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

    @classmethod
    def push_valid_bundle(cls, staged_bundle: StagingBundle, user_obj: User) -> None:
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
            RuntimeError: an unexpected error, something we already checked
                has failed.
            PlomPushCollisionException
            ValueError
            ObjectDoesNotExist
        """
        if not PapersPrinted.have_papers_been_printed():
            raise RuntimeError("Papers have not yet been printed.")

        bundle_images = StagingImage.objects.filter(
            bundle=staged_bundle
        ).prefetch_related("baseimage")

        # Staging has checked this - but we check again here to be very sure
        if not cls.all_staged_imgs_valid(bundle_images):
            raise RuntimeError("Some pages in this bundle do not have QR data.")

        # Staging has not checked this - we need to do it here
        collide = cls.find_internal_collisions(bundle_images)
        if len(collide) > 0:
            # just make a list of bundle-orders of the colliding images
            collide_error_list = [[Y.bundle_order for Y in X] for X in collide]
            raise PlomPushCollisionException(
                f"Some images within the staged bundle collide with each-other: {collide_error_list}"
            )

        # Staging has not checked this - we need to do it here
        colliding_stagingimages = cls._find_external_collisions(bundle_images)
        if len(collide) > 0:
            # just make a list of bundle-orders of the colliding images
            colliding_orders = sorted([X.bundle_order for X in colliding_stagingimages])
            collisions = format_int_list_with_runs(colliding_orders)
            raise PlomPushCollisionException(
                f"Some images in the staged bundle collide with uploaded pages: {collisions}"
            )

        uploaded_bundle = Bundle(
            name=staged_bundle.slug,
            pdf_hash=staged_bundle.pdf_hash,
            user=user_obj,
            staging_bundle=staged_bundle,
        )
        uploaded_bundle.save()

        # we create all the images as O(n) but then update
        # fixed-pages and associated structures in O(1) - I hope
        new_mobile_pages = []
        new_discard_pages = []
        updated_fixed_pages = []
        # we need all the fixed pages that are touched by these new images
        # to get that we find all the papers that are touched and
        # then get **all** the fixed pages from those papers.
        paper_numbers = set(
            staged.paper_number
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
                # This handles all types of FixedPages: Question, ID and DNM
                fp_list = fixedpage_by_pn_pg[(staged.paper_number, staged.page_number)]
                if len(fp_list) == 0:
                    raise ObjectDoesNotExist(
                        f"Paper {staged.paper_number}"
                        f" page {staged.page_number} does not exist"
                    )
                for fp in fp_list:
                    fp.image = image
                    updated_fixed_pages.append(fp)

            elif staged.image_type == StagingImage.EXTRA:
                # need to make one mobile page for each question in the question-list
                paper = Paper.objects.get(paper_number=staged.paper_number)
                for q in staged.question_idx_list:
                    # get the version from the paper/question info
                    v = PaperInfoService.get_version_from_paper_question(
                        staged.paper_number, q
                    )
                    # defer actual DB creation to bulk operation later
                    new_mobile_pages.append(
                        MobilePage(
                            paper=paper, image=image, question_index=q, version=v
                        )
                    )
                # otherwise, if question index list empty, make a non-marked MobilePage
                if not staged.question_idx_list:
                    new_mobile_pages.append(
                        MobilePage(
                            paper=paper,
                            image=image,
                            question_index=MobilePage.DNM_qidx,
                            version=0,
                        )
                    )
            elif staged.image_type == StagingImage.DISCARD:
                new_discard_pages.append(
                    DiscardPage(image=image, discard_reason=staged.discard_reason)
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
        ready = cls._get_ready_questions_in_bundle(uploaded_bundle)
        MarkingTaskService.bulk_create_and_update_marking_tasks(ready)

        # bulk create the associated ID tasks in O(1).
        papers = [
            id_page.paper for id_page in cls._get_id_pages_in_bundle(uploaded_bundle)
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

    # TODO: why is this method here instead of in the staging code?
    @staticmethod
    @transaction.atomic
    def all_staged_imgs_valid(staged_imgs: QuerySet[StagingImage]) -> bool:
        """Check that all staged images in the bundle are ready to be uploaded.

        Each image must be "known" or "discard" or be
        "extra" with data. There can be no "unknown", "unread",
        "error" or "extra"-without-data.

        Args:
            staged_imgs: QuerySet, a list of all staged images for a bundle

        Returns:
            True if all images are valid, False otherwise.
        """
        # conflict if imported at top
        from plom_server.Scan.services import ScanService

        # while this is done by staging, we redo it here to be **very** sure.
        if staged_imgs.filter(
            image_type__in=[
                StagingImage.UNREAD,
                StagingImage.UNKNOWN,
                StagingImage.ERROR,
            ]
        ).exists():
            return False
        # All Extra images must be assigned
        extras = staged_imgs.filter(image_type=StagingImage.EXTRA)
        if not ScanService.do_all_these_extra_images_have_data(extras):
            return False
        # to do the complement of this search we'd need to count
        # knowns, discards and extra-with-data and make sure that
        # total matches number of pages in the bundle.
        return True

    @staticmethod
    @transaction.atomic
    def find_internal_collisions(
        staged_imgs: QuerySet[StagingImage],
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
        for img in staged_imgs.filter(image_type=StagingImage.KNOWN):
            tpv = encodePaperPageVersion(img.paper_number, img.page_number, img.version)
            # append this image.primary-key to the list of images with that tpv
            known_imgs.setdefault(tpv, []).append(img.pk)
        for tpv, image_list in known_imgs.items():
            if len(image_list) == 1:  # no collision at this tpv
                continue
            collisions.append(image_list)

        return collisions

    @staticmethod
    @transaction.atomic
    def _find_external_collisions(
        staged_imgs: QuerySet[StagingImage],
    ) -> QuerySet[StagingImage]:
        """Check staged images for collisions with already pushed page images.

        Note that this function can only check unpushed StagedImages.
        If you ask about a pushed StagedImage, it will always be flagged
        as "colliding".

        Args:
            staged_imgs: A queryset of StagedImages.

        Returns:
            A queryset of any input StagedImages which collide with
            already pushed images. If there are no collisions, an
            empty queryset is returned.
        """
        # we want something like this:
        # SELECT *
        # FROM StagingImage INNER JOIN FixedPage
        # WHERE FixedPage.image IS NOT NULL
        # ON StagingImage.paper_number = FixedPage.paper.paper_number AND StagingImage.page_number = FixedPage.page_number;

        # Django can't construct direct JOINs unless there is an
        # explicit reference between each table (i.e., an FK connecting
        # them), so we need to do something less direct.

        # This is logically equivalent to the above query, but
        # not quite as efficient (it's still very efficient)
        fixed_pages = FixedPage.objects.filter(
            image__isnull=False,
            paper__paper_number=OuterRef("paper_number"),
            page_number=OuterRef("page_number"),
        )
        colliding_staged_imgs = staged_imgs.annotate(
            colliding=Exists(fixed_pages)
        ).filter(colliding=True)

        return colliding_staged_imgs

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
        question_pages = FixedPage.objects.filter(
            image__bundle=bundle, page_type=FixedPage.QUESTIONPAGE
        )
        extras = MobilePage.objects.filter(image__bundle=bundle)
        # Note ready/nonready is about *questions*, so any MobilePages attached to DNM don't
        # count (including them will lead to bugs, Issue #3925); we filter them out.
        extras = extras.exclude(question_index=MobilePage.DNM_qidx)

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
        paper_question_pairs_dict = (
            ImageBundleService.check_if_paper_question_pairs_ready(
                [t[:2] for t in papers_questions_versions_updated_by_bundle]
            )
        )
        pqv_updated_and_ready = [
            t
            for t in papers_questions_versions_updated_by_bundle
            if paper_question_pairs_dict[t[:2]]
        ]
        return pqv_updated_and_ready

    @staticmethod
    def _get_id_pages_in_bundle(bundle: Bundle) -> QuerySet[FixedPage]:
        """Get all of the ID pages in an uploaded bundle, in order to initialize ID tasks.

        Args:
            bundle: a Bundle instance

        Returns:
            A query of only the ID pages in the input bundle
        """
        return FixedPage.objects.filter(
            image__bundle=bundle, page_type=FixedPage.IDPAGE
        ).prefetch_related("paper")

    @staticmethod
    def is_given_paper_ready_for_id_ing(paper_obj: Paper) -> bool:
        """Check if the id page of the given paper has an image and so is ready for id-ing.

        Args:
            paper_obj (Paper): the database paper to check

        Returns:
            bool: true when paper is ready for id-ing (ie the ID page has an image)
        """
        return FixedPage.objects.filter(
            paper=paper_obj,
            page_type=FixedPage.IDPAGE,
            image__isnull=False,
        ).exists()

    @staticmethod
    @transaction.atomic
    def _get_ready_paper_question_pairs() -> list[tuple[int, int]]:
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
        filled_qpages = FixedPage.objects.filter(
            image__isnull=False, page_type=FixedPage.QUESTIONPAGE
        )
        mpages = MobilePage.objects.all()
        # Note ready/nonready is about *questions*, so any MobilePages attached to DNM don't
        # count (including them will lead to bugs, Issue #3925); we filter them out.
        mpages = mpages.exclude(question_index=MobilePage.DNM_qidx)

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

    @classmethod
    def check_if_paper_question_pairs_ready(
        cls, paper_qidx_pairs: list[tuple[int, int]]
    ) -> dict[tuple[int, int], bool]:
        """Check if provided paper/question pairs are ready for marking, returning a dict.

        See :func:`_get_ready_paper_question_pairs` for what 'ready' means.

        Args:
            paper_qidx_pairs: a list of tuples identifying a particular
                question on a particular paper. The tuples should be formatted
                as (paper_number, qidx).  You should not ask about any "meta
                values" such as extra pages assigned to DNM: valid qidx's only
                in the range 1 to the largest question index.

        Returns:
            A dict with the input paper number/qidx tuples as keys, and True/False
            as the values.

        Raises:
            ValueError: asking about invalid question indices.
        """
        valid_question_indices = SpecificationService.get_question_indices()
        ready_pairs = cls._get_ready_paper_question_pairs()
        pq_pair_ready = {}
        for pair in paper_qidx_pairs:
            if pair[1] not in valid_question_indices:
                raise ValueError(
                    f"question index '{pair[1]}' doesn't correspond"
                    " to any question on this assessment."
                )
            pq_pair_ready[pair] = pair in ready_pairs
        return pq_pair_ready
