# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2022 Brennen Chiu
# Copyright (C) 2023 Natalie Balashov
# Copyright (C) 2023 Julian Lapenna
# Copyright (C) 2023-2025 Andrew Rechnitzer
# Copyright (C) 2024-2026 Colin B. Macdonald
# Copyright (C) 2025 Aidan Murphy

from typing import Any

from django.db import transaction
from django.db.models import Exists, OuterRef, Prefetch, Count
from django.db.models.query import QuerySet

from plom_server.Papers.models import (
    FixedPage,
    MobilePage,
    DiscardPage,
    Paper,
    Image,
    Bundle,
)
from plom_server.Papers.services import SpecificationService
from ..models import StagingBundle


class ManageScanService:
    """Functions for overseeing pushed papers."""

    def get_total_fixed_pages(self) -> int:
        """Return the total number of fixed pages."""
        return FixedPage.objects.count()

    def get_total_mobile_pages(self) -> int:
        """Return the total number of mobile pages.

        Note that an image used for multiple questions will be counted
        with multiplicity.
        """
        return MobilePage.objects.count()

    @transaction.atomic
    def get_number_of_scanned_pages(self) -> int:
        """Return the number of pages scanned and validated.

        Note that any mobile page used in multiple questions is
        counted with multiplicity.
        """
        scanned_fixed = FixedPage.objects.exclude(image=None)
        mobile = MobilePage.objects.all()
        return scanned_fixed.count() + mobile.count()

    @staticmethod
    def get_total_papers() -> int:
        """Return the total number of papers in the exam."""
        return Paper.objects.all().count()

    @staticmethod
    def _get_used_unused_paper_querysets() -> tuple[QuerySet, QuerySet]:
        """Return lazy querysets for all used and unused papers.

        A paper is used when it has at least one fixed page image, or at
        least one mobile page. A paper is unused when it has no fixed pages,
        and no mobile pages.

        Returns:
            A tuple containing two (lazy) querysets - the first queryset contains
            all used papers, the second contains all unused papers.
        """
        # Get fixed pages with image - ie scanned.
        fixed_with_scan = FixedPage.objects.filter(
            paper=OuterRef("pk"), image__isnull=False
        )
        # Get papers with neither fixed-with-scan nor mobile-pages
        no_images_at_all = Paper.objects.filter(
            ~Exists(fixed_with_scan), mobilepage__isnull=True
        )

        unused_papers_queryset = no_images_at_all
        # all papers must be used or unused
        used_papers_queryset = Paper.objects.filter(
            ~Exists(
                unused_papers_queryset.filter(paper_number=OuterRef("paper_number"))
            )
        )

        return used_papers_queryset, unused_papers_queryset

    @classmethod
    def _get_complete_incomplete_paper_querysets(cls) -> tuple[QuerySet, QuerySet]:
        """Return lazy querysets for all complete and incomplete papers.

        A paper is complete when it either has **all** its fixed
        pages, or it has no fixed pages but has mobile pages for all
        spec questions.
        A paper is incomplete when it has *some* but not all its
        fixed pages. A paper is also incomplete when it contains no fixed
        pages, but has mobile pages for some, but not all, questions.
        Note that the sets of complete and incomplete papers are: mutually exclusive
        and exhaustive of all used papers, i.e. all used papers must be complete
        or incomplete.

        Returns:
            A tuple containing two (lazy) querysets - the first queryset contains
            all complete papers, the second contains all incomplete papers.
        """
        # Get fixed pages with no image
        fixed_with_no_scan = FixedPage.objects.filter(paper=OuterRef("pk"), image=None)
        # Get papers without fixed-page-with-no-scan
        all_fixed_present = Paper.objects.filter(~Exists(fixed_with_no_scan))
        # now get papers with **no** fixed page scans
        fixed_with_scan = FixedPage.objects.filter(
            paper=OuterRef("pk"), image__isnull=False
        )

        # we save one query by asking directly for questions, rather than the spec
        exam_question_indices: list = SpecificationService.get_question_indices()
        if not exam_question_indices:
            # Short-circuit return: with no spec, scanning project is degenerate
            return Paper.objects.none(), Paper.objects.none()

        # build a subquery to help us find papers which have at least one mobile page
        # with a distinct question_index for each question.
        mobile_pages = (
            MobilePage.objects.values("paper")
            # filter out pages with meta question indexes (such as DNM Pages)
            .filter(question_index__in=exam_question_indices)
            .annotate(counts=Count("question_index", distinct=True))
            .filter(counts=len(exam_question_indices))
            .values_list("paper", flat=True)
        )
        all_mobile_pages = MobilePage.objects.filter(
            paper__in=mobile_pages, paper=OuterRef("pk")
        )
        no_fixed_but_all_mobile = Paper.objects.filter(
            ~Exists(fixed_with_scan), Exists(all_mobile_pages)
        )

        complete_papers_queryset = all_fixed_present | no_fixed_but_all_mobile

        # all used papers must be complete or incomplete
        used_papers_queryset, __ = cls._get_used_unused_paper_querysets()
        incomplete_papers_queryset = used_papers_queryset.filter(
            ~Exists(
                complete_papers_queryset.filter(paper_number=OuterRef("paper_number"))
            )
        )

        return complete_papers_queryset, incomplete_papers_queryset

    @classmethod
    def get_number_completed_papers(cls) -> int:
        """Returns the number of complete papers."""
        complete_papers_queryset, __ = cls._get_complete_incomplete_paper_querysets()
        return complete_papers_queryset.count()

    # do not call this in a loop - write a function:
    # def are_papers_completely_scanned(self, paper_nums: list[int]) -> dict[int: bool]
    @classmethod
    def is_paper_completely_scanned(cls, paper_num: int) -> bool:
        """Check whether the given paper has been completely scanned."""
        complete_papers_queryset, __ = cls._get_complete_incomplete_paper_querysets()
        return complete_papers_queryset.filter(paper_number=paper_num).exists()

    @classmethod
    @transaction.atomic
    def get_all_complete_papers(cls) -> dict[int, dict[str, list[dict[str, Any]]]]:
        """Dicts of info about papers that are completely scanned.

        see :func: `_get_complete_incomplete_paper_querysets` for definitions
        of complete and incomplete papers.

        Returns:
            Dict keyed by paper number and then for each we have keys
            "fixed" and "mobile".  Under each of those we have a list of
            dicts of key-value pairs about pages.  The information in
            "fixed" and "mobile" case is different, for example "mobile"
            have page labels and "fixed" do not.
        """
        # Foreign key objects (in this case FixedPage and MobilePage) aren't
        # fetched until they are accessed by a Model-object (Paper)
        # they reference. If we are iterating over many Paper objects (1000's)
        # we must "prefetch" the foreign keys to prevent several DB queries for
        # each paper (a db query for each mobile/fixed page accessed).
        complete_papers_queryset, __ = cls._get_complete_incomplete_paper_querysets()

        complete_papers_queryset = complete_papers_queryset.prefetch_related(
            Prefetch(
                "fixedpage_set", queryset=FixedPage.objects.order_by("page_number")
            ),
            # Papers/models/structure.py claims MobilePages have no order so sort by id
            Prefetch(
                "mobilepage_set",
                queryset=MobilePage.objects.order_by("question_index", "pk"),
            ),
            "fixedpage_set__image",
            "mobilepage_set__image",
        )

        complete: dict[int, Any] = {}  # more precise typing in defn
        for paper in complete_papers_queryset:
            complete[paper.paper_number] = {"fixed": [], "mobile": []}
            # notice we don't specify order or prefetch in the loops
            # below here because we did the hard work above
            for fp in paper.fixedpage_set.all():
                # TODO: only need to check the first fixed page before skipping
                if fp.image_id is None:
                    continue
                complete[paper.paper_number]["fixed"].append(
                    {
                        "page_number": fp.page_number,
                        "img_pk": fp.image.pk,
                        "page_pk": fp.pk,
                    }
                )
            for mp in paper.mobilepage_set.all():
                complete[paper.paper_number]["mobile"].append(
                    {
                        "question_idx": mp.question_index,
                        "img_pk": mp.image.pk,
                        "page_pk": mp.pk,
                        "page_label": (
                            "dnm"
                            if mp.question_index == MobilePage.DNM_qidx
                            else f"qi.{mp.question_index}"
                        ),
                    }
                )
        return complete

    @classmethod
    @transaction.atomic
    def get_all_incomplete_papers(cls) -> dict[int, dict[str, list[dict[str, Any]]]]:
        """Dicts of info about papers that are partially but not completely scanned.

        see :func: `_get_complete_incomplete_paper_querysets` for definitions
        of complete and incomplete papers.

        Returns:
            Dict keyed by paper number and then for each we have keys
            "fixed" and "mobile".  Under each of those we have a list of
            dicts of key-value pairs about pages.  The information in
            "fixed" and "mobile" case is different, for example "mobile"
            have page labels and "fixed" do not.
        """
        _, incomplete_papers_queryset = cls._get_complete_incomplete_paper_querysets()

        incomplete_papers_queryset = incomplete_papers_queryset.prefetch_related(
            Prefetch(
                "fixedpage_set", queryset=FixedPage.objects.order_by("page_number")
            ),
            Prefetch(
                "mobilepage_set",
                queryset=MobilePage.objects.order_by("question_index", "pk"),
            ),
            "fixedpage_set__image",
            "mobilepage_set__image",
        )

        incomplete: dict[int, Any] = {}  # more precise typing in defn
        for paper in incomplete_papers_queryset:
            incomplete[paper.paper_number] = {"fixed": [], "mobile": []}
            for fp in paper.fixedpage_set.all():
                if fp.image:
                    incomplete[paper.paper_number]["fixed"].append(
                        {
                            "status": "present",
                            "page_number": fp.page_number,
                            "page_pk": fp.pk,
                            "img_pk": fp.image.pk,
                        }
                    )
                else:
                    incomplete[paper.paper_number]["fixed"].append(
                        {
                            "status": "missing",
                            "page_number": fp.page_number,
                            "page_pk": fp.pk,
                            "kind": fp.get_page_type_display(),
                        }
                    )
            # if no fixed pages, assume mobile page only paper
            paper_checks = [
                p["status"] == "missing"
                for p in incomplete[paper.paper_number]["fixed"]
            ]
            if all(paper_checks):
                incomplete[paper.paper_number]["fixed"] = []

            for mp in paper.mobilepage_set.all():
                incomplete[paper.paper_number]["mobile"].append(
                    {
                        "question_idx": mp.question_index,
                        "img_pk": mp.image.pk,
                        "page_pk": mp.pk,
                        "page_label": (
                            "dnm"
                            if mp.question_index == MobilePage.DNM_qidx
                            else f"qi.{mp.question_index}"
                        ),
                    }
                )
        return incomplete

    @classmethod
    def get_number_incomplete_papers(cls) -> int:
        """Return the number of papers partially but not completely scanned."""
        __, incomplete_papers_queryset = cls._get_complete_incomplete_paper_querysets()
        return incomplete_papers_queryset.count()

    @transaction.atomic
    def get_number_unused_papers(self) -> int:
        """Return the number of papers that are unused."""
        _, unused_papers_queryset = self._get_used_unused_paper_querysets()
        return unused_papers_queryset.count()

    @classmethod
    def get_all_unused_papers(cls) -> list[int]:
        """Return a list of paper-numbers of all unused papers.

        see :func: `_get_used_unused_paper_querysets` for definitions
        of used and unused papers.

        Returns:
            a list of integers sorted in paper-number order.

        TODO: currently, and ironically, "unused" (but tested)
        """
        __, unused_papers_queryset = cls._get_used_unused_paper_querysets()
        return sorted([paper.paper_number for paper in unused_papers_queryset])

    @classmethod
    def get_all_used_papers(cls) -> list[int]:
        """Return a list of paper-numbers of all used papers.

        see :func: `_get_used_unused_paper_querysets` for definitions
        of used and unused papers.

        Returns:
            a list of paper-numbers sorted numerically.
        """
        used_papers_queryset, _ = cls._get_used_unused_paper_querysets()
        return sorted([paper.paper_number for paper in used_papers_queryset])

    @staticmethod
    def get_pushed_bundles_w_staging_prefetch() -> QuerySet[Bundle]:
        """Get all the pushed Bundles, with a prefetch on the related Staging Bundles."""
        return Bundle.objects.filter(_is_system=False).prefetch_related(
            "staging_bundle"
        )

    def get_number_pushed_bundles(self) -> int:
        """Return the number of pushed bundles (excluding system bundles)."""
        return Bundle.objects.filter(_is_system=False).count()

    def get_number_unpushed_bundles(self) -> int:
        """Return the number of uploaded, but not yet pushed, bundles."""
        return StagingBundle.objects.filter(pushed=False).count()

    def get_pushed_image(self, img_pk: int) -> Image | None:
        """Return a database Image object with the given pk or None if it does not exist."""
        try:
            return Image.objects.select_related("baseimage").get(pk=img_pk)
        except Image.DoesNotExist:
            return None

    @transaction.atomic
    def get_pushed_fixed_page_image_info(self, page_pk: int) -> dict[str, Any]:
        """Given the pk of the fixed-page return info about it and its image.

        Args:
            page_pk: the pk of the fixed-page.

        Returns: A dict with keys
            * page_type: always "fixed"
            * paper_number: the paper containing that fixed page.
            * page_number: the page_number of the fixed page.
            * version: the version of the fixed page.
            * image_pk: the pk of the image in the fixed page.
            * bundle_name: the name of the bundle containing the image.
            * bundle_order: the order of the image inside the bundle.
        """
        fp_obj = FixedPage.objects.get(pk=page_pk)
        if fp_obj.image is None:
            return {
                "page_type": "fixed",
                "paper_number": fp_obj.paper.paper_number,
                "page_number": fp_obj.page_number,
                "version": fp_obj.version,
                "image_pk": None,
                "bundle_name": None,
                "bundle_order": None,
            }
        else:
            return {
                "page_type": "fixed",
                "paper_number": fp_obj.paper.paper_number,
                "page_number": fp_obj.page_number,
                "version": fp_obj.version,
                "image_pk": fp_obj.image.pk,
                "bundle_name": fp_obj.image.bundle.name,
                "bundle_order": fp_obj.image.bundle_order,
            }

    @transaction.atomic
    def get_pushed_mobile_page_image_info(self, page_id: int) -> dict[str, Any]:
        """Given the pk of the mobile-page return info about it and its image.

        Args:
            page_id: the id of the mobile-page.

        Returns:
            A dict with keys:
                * page_type: always "mobile".
                * paper_number: the paper containing that fixed page.
                * image_pk: the pk of the image in the fixed page.
                * bundle_name: the name of the bundle containing the image.
                * bundle_order: the order of the image inside the bundle.
                * question_idx_list: the list of positive question
                  indices which share the underlying image.  If an
                  image is used in two MobilePages with different
                  question-indices, both indices will be in this list.
                  Note the list can be empty, for example if this
                  image is only in MobilePages that do not correspond
                  to questions.  (these would be DNM in general).
                * question_list_html: nice html rendering of the list
                  of questions.  Will be the string "None" if the list
                  is empty.

        Raises:
            None expected.
        """
        mp_obj = MobilePage.objects.get(pk=page_id)
        img = mp_obj.image
        # same image might be used for multiple questions - get all those
        q_idx_list = [
            mp_obj.question_index
            for mp_obj in MobilePage.objects.filter(image=img)
            if mp_obj.question_index != MobilePage.DNM_qidx
        ]
        _render = SpecificationService.render_html_flat_question_label_list
        return {
            "page_type": "mobile",
            "paper_number": mp_obj.paper.paper_number,
            "question_idx_list": q_idx_list,
            "question_list_html": _render(q_idx_list),
            "image_pk": img.pk,
            "bundle_name": img.bundle.name,
            "bundle_order": img.bundle_order,
        }

    @transaction.atomic
    def get_pushed_discard_page_image_info(self, page_pk: int) -> dict[str, Any]:
        """Given the pk of the discard-page return info about it and its image.

        Args:
            page_pk: the pk of the discard-page.

        Returns: A dict with keys
            * page_type: always "discard"
            * reason: a reason that the page was discarded.
            * image_pk: the pk of the image in the fixed page.
            * bundle_name: the name of the bundle containing the image.
            * bundle_order: the order of the image inside the bundle.
        """
        dp_obj = DiscardPage.objects.get(pk=page_pk)
        return {
            "page_type": "discard",
            "image_pk": dp_obj.image.pk,
            "reason": dp_obj.discard_reason,
            "bundle_name": dp_obj.image.bundle.name,
            "bundle_order": dp_obj.image.bundle_order,
        }

    @staticmethod
    def get_n_images_in_pushed_bundle(bundle: Bundle | int) -> int:
        """Get the number of page images in a Bundle from the number of Images.

        This could be the same thing as :method:`ScanService.get_n_images` but
        semantically it might be sometimes more correct to query the Bundle
        not the StagingBundle.
        """
        if isinstance(bundle, int):
            return Image.objects.filter(bundle_id=bundle).count()
        return Image.objects.filter(bundle=bundle).count()

    @staticmethod
    def get_n_discards_in_pushed_bundle(bundle: Bundle | int) -> int:
        """Count how many DiscardPage a pushed bundle has.

        Args:
            bundle: a pushed bundle, not a staging bundle.  You can pass
                either the Django Bundle objects or an integer ID.

        Raises:
            ObjectDoesNotExist: if you pass an invalid bundle id.
        """
        if isinstance(bundle, int):
            return DiscardPage.objects.filter(image__bundle_id=bundle).count()
        return DiscardPage.objects.filter(image__bundle=bundle).count()

    @transaction.atomic
    def get_discarded_page_info(self) -> list[dict[str, Any]]:
        """Get information on all discarded pages.

        Returns:
            A list of dicts - one for each discard page. Each dict contains
            * "page_pk": the pk of the discard page.
            * "reason": the reason the page was discarded.
            * "image_pk": the pk of the underlying image.
            * "bundle_pk": the pk of the bundle containing the image.
            * "bundle_name": the name of the bundle.
            * "order": the order of the image within the bundle.

        """
        discards = []
        for dp_obj in DiscardPage.objects.all().prefetch_related("image__bundle"):
            img = dp_obj.image
            discards.append(
                {
                    "page_pk": dp_obj.pk,
                    "reason": dp_obj.discard_reason,
                    "bundle_pk": img.bundle.pk,
                    "bundle_name": img.bundle.name,
                    "order": img.bundle_order,
                    "image_pk": img.pk,
                }
            )

        return discards

    def get_page_images_in_paper(self, paper_number: int) -> list[dict[str, Any]]:
        """Return the fixed/mobile pages in the paper and their images.

        Args:
            paper_number: which paper.

        Returns:
            List of the fixed pages and mobile pages in
            the given paper. For each fixed page a dict with
            page-number, page-type (ie fixed), the page pk, and the
            image pk is given (if it exists). For each mobile page the
            page-type (mobile), the question index, the page pk and
            image pk is given. Note that a mobile page *must* have an
            associated image, while a fixed page may not.

        Raises:
            ValueError: paper not in database.
        """
        try:
            paper_obj = Paper.objects.get(paper_number=paper_number)
        except Paper.DoesNotExist as e:
            raise ValueError(f"Paper {paper_number} is not in the database") from e

        page_images = []
        for fp_obj in (
            paper_obj.fixedpage_set.all()
            .order_by("page_number")
            .select_related("image")
        ):
            if fp_obj.page_type == FixedPage.QUESTIONPAGE:
                qidx_field = fp_obj.question_index
            else:
                qidx_field = ""
            dat = {
                "page_type": "fixed",
                "page_number": fp_obj.page_number,
                "page_pk": fp_obj.pk,
                "question_index": qidx_field,
            }
            if fp_obj.image:
                dat.update({"image": fp_obj.image.pk})
            else:
                dat.update({"image": None})
            page_images.append(dat)
        for mp_obj in (
            paper_obj.mobilepage_set.all()
            .order_by("question_index")
            .select_related("image")
        ):
            dat = {
                "page_type": "mobile",
                "question_index": mp_obj.question_index,
                "page_pk": mp_obj.pk,
            }
            dat.update({"image": mp_obj.image.pk})
            page_images.append(dat)

        return page_images

    @transaction.atomic
    def get_papers_missing_fixed_pages(self) -> list[tuple[int, list[int]]]:
        """Return a list of the missing fixed pages in papers.

        Returns:
            A list of pairs `(paper_number (int), [missing fixed pages (int)])`.
        """
        # Get fixed pages with no image - ie not scanned.
        fixed_with_no_scan = FixedPage.objects.filter(
            paper=OuterRef("pk"), image__isnull=True
        )
        # Get fixed pages with image - ie scanned.
        fixed_with_scan = FixedPage.objects.filter(
            paper=OuterRef("pk"), image__isnull=False
        )

        # Get papers with some but not all scanned fixed pages
        some_but_not_all_fixed_present = Paper.objects.filter(
            Exists(fixed_with_no_scan), Exists(fixed_with_scan)
        ).prefetch_related(
            Prefetch(
                "fixedpage_set", queryset=FixedPage.objects.order_by("page_number")
            ),
            "fixedpage_set__image",
        )
        missing_paper_fixed_pages = []
        for paper in some_but_not_all_fixed_present:
            dat = []
            for fp in paper.fixedpage_set.all():
                if not fp.image:
                    dat.append(fp.page_number)
            missing_paper_fixed_pages.append((paper.paper_number, dat))

        return missing_paper_fixed_pages
