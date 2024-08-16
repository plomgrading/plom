# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2022 Brennen Chiu
# Copyright (C) 2023 Natalie Balashov
# Copyright (C) 2023-2024 Andrew Rechnitzer
# Copyright (C) 2023 Julian Lapenna
# Copyright (C) 2024 Colin B. Macdonald

from __future__ import annotations

from typing import Any

import arrow

from django.db import transaction
from django.db.models import Exists, OuterRef, Prefetch

from Papers.models import (
    FixedPage,
    MobilePage,
    Paper,
    Image,
    Bundle,
)
from Papers.services import SpecificationService
from Scan.models import StagingBundle


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

    def get_total_test_papers(self) -> int:
        """Return the total number of test-papers in the exam."""
        return Paper.objects.all().count()

    @transaction.atomic
    def get_number_completed_test_papers(self) -> int:
        """Return a dict of completed papers and their fixed/mobile pages.

        A paper is complete when it either has **all** its fixed
        pages, or it has no fixed pages but has some extra-pages.
        """
        # Get fixed pages with no image
        fixed_with_no_scan = FixedPage.objects.filter(paper=OuterRef("pk"), image=None)
        # Get papers without fixed-page-with-no-scan
        all_fixed_present = Paper.objects.filter(~Exists(fixed_with_no_scan))
        # now get papers with **no** fixed page scans
        fixed_with_scan = FixedPage.objects.filter(
            paper=OuterRef("pk"), image__isnull=False
        )
        # build a subquery to help us find papers which have some
        # mobile_pages the outer-ref in the subquery allows us to
        # match for papers that have mobile pages. This also allows us
        # to avoid duplications since "exists" stops the query as soon
        # as one item is found - see below
        mobile_pages = MobilePage.objects.filter(paper=OuterRef("pk"))
        no_fixed_but_some_mobile = Paper.objects.filter(
            ~Exists(fixed_with_scan), Exists(mobile_pages)
        )
        # We can also do the above query as:
        #
        # no_fixed_but_some_mobile = Paper.objects.filter(
        # ~Exists(fixed_with_scan), mobilepages_set__isnull=False
        # ).distinct()
        #
        # however this returns one result for **each** mobile-page, so
        # one needs to append the 'distinct'. This is a common problem
        # when querying backwards across foreign key fields

        return all_fixed_present.count() + no_fixed_but_some_mobile.count()

    def is_paper_completely_scanned(self, paper_number: int) -> bool:
        """Test whether given paper has been completely scanned.

        A paper is complete when it either has **all** its fixed
        pages, or it has no fixed pages but has some extra-pages.
        """
        # paper is completely scanned
        try:
            paper_obj = Paper.objects.get(paper_number=paper_number)
        except Paper.DoesNotExist:
            return False

        # fixed_count = FixedPage.objects.filter(paper=paper_obj).count()
        fixed_with_no_scan_count = FixedPage.objects.filter(
            paper=paper_obj, image=None
        ).count()
        fixed_with_scan_count = FixedPage.objects.filter(
            paper=paper_obj, image__isnull=False
        ).count()

        # if all fixed pages have scans - then complete
        if fixed_with_no_scan_count == 0:
            return True
        # if no fixed pages have scans, but have some mobile pages, then complete
        mobile_page_count = MobilePage.objects.filter(paper=paper_obj).count()
        if fixed_with_scan_count == 0 and mobile_page_count > 0:
            return True
        # else we have (fixed_no_scan > 0) and (fixed_with_scan > 0 or mobile_pages==0)
        # = (fixed no scan>0, fixed with scan > 0) or (fixed no scan > 0 and mobile pages = 0)
        # paper is not completely scanned in those cases
        return False

    @transaction.atomic
    def get_all_completed_test_papers(self) -> dict[int, dict[str, Any]]:
        """Return dict of test-papers that have been completely scanned.

        A paper is complete when it either has **all** its fixed
        pages, or it has no fixed pages but has some extra-pages.
        """
        # Subquery of fixed pages with no image
        fixed_with_no_scan = FixedPage.objects.filter(paper=OuterRef("pk"), image=None)
        # Get all papers without fixed-page-with-no-scan
        all_fixed_present = Paper.objects.filter(
            ~Exists(fixed_with_no_scan)
        ).prefetch_related(
            Prefetch(
                "fixedpage_set", queryset=FixedPage.objects.order_by("page_number")
            ),
            Prefetch(
                "mobilepage_set",
                queryset=MobilePage.objects.order_by("question_index"),
            ),
            "fixedpage_set__image",
            "mobilepage_set__image",
        )
        # Notice all the prefetching here - this is to avoid N+1
        # problems.  Below we loop over these papers and their pages /
        # images we tell django to prefetch the fixed and mobile
        # pages, and the images in the fixed and mobile pages.  Since
        # there are many fixed/mobile pages for a given paper, these
        # are fixedpage_set and mobilepage_set. Now because we want to
        # loop over the fixed/mobile pages in specific orders we use
        # the Prefetch object to specify that order at the time of
        # prefetching.

        # now subquery papers with **no** fixed page scans
        fixed_with_scan = FixedPage.objects.filter(
            paper=OuterRef("pk"), image__isnull=False
        )
        # again - we use a subquery to get mobile pages to avoid
        # duplications when executing the main query (see the
        # get_number_completed_test_papers function above.
        mobile_pages = MobilePage.objects.filter(paper=OuterRef("pk"))
        no_fixed_but_some_mobile = Paper.objects.filter(
            ~Exists(fixed_with_scan), Exists(mobile_pages)
        ).prefetch_related(
            Prefetch(
                "mobilepage_set",
                queryset=MobilePage.objects.order_by("question_index"),
            ),
            "mobilepage_set__image",
        )
        # again since we loop over the mobile pages within the paper
        # in a specified order, and ref the image in those mobile-pages
        # we do all this prefetching.

        complete: dict[int, dict[str, Any]] = {}
        for paper in all_fixed_present:
            complete[paper.paper_number] = {"fixed": [], "mobile": []}
            # notice we don't specify order or prefetch in the loops
            # below here because we did the hard work above
            for fp in paper.fixedpage_set.all():
                complete[paper.paper_number]["fixed"].append(
                    {
                        "page_number": fp.page_number,
                        "img_pk": fp.image.pk,
                    }
                )
            for mp in paper.mobilepage_set.all():
                complete[paper.paper_number]["mobile"].append(
                    {
                        "question_number": mp.question_index,
                        "img_pk": mp.image.pk,
                    }
                )
        for paper in no_fixed_but_some_mobile:
            complete[paper.paper_number] = {"fixed": [], "mobile": []}
            # again we don't specify order or prefetch here because of the work above
            for mp in paper.mobilepage_set.all():
                complete[paper.paper_number]["mobile"].append(
                    {
                        "question_number": mp.question_index,
                        "img_pk": mp.image.pk,
                    }
                )
        return complete

    @transaction.atomic
    def get_all_incomplete_test_papers(self) -> dict[int, dict[str, Any]]:
        """Return a dict of test-papers that are partially but not completely scanned.

        A paper is not completely scanned when it has *some* but not all its fixed pages.
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
            Prefetch(
                "mobilepage_set",
                queryset=MobilePage.objects.order_by("question_index"),
            ),
            "fixedpage_set__image",
            "mobilepage_set__image",
        )

        incomplete: dict[int, dict[str, Any]] = {}
        for paper in some_but_not_all_fixed_present:
            incomplete[paper.paper_number] = {"fixed": [], "mobile": []}
            for fp in paper.fixedpage_set.all():
                if fp.image:
                    incomplete[paper.paper_number]["fixed"].append(
                        {
                            "status": "present",
                            "page_number": fp.page_number,
                            "img_pk": fp.image.pk,
                        }
                    )
                else:
                    incomplete[paper.paper_number]["fixed"].append(
                        {
                            "status": "missing",
                            "page_number": fp.page_number,
                        }
                    )
            for mp in paper.mobilepage_set.all():
                incomplete[paper.paper_number]["mobile"].append(
                    {
                        "question_number": mp.question_index,
                        "img_pk": mp.image.pk,
                    }
                )

        return incomplete

    @transaction.atomic
    def get_number_incomplete_test_papers(self) -> int:
        """Return the number of test-papers that are partially but not completely scanned.

        A paper is not completely scanned when it has *some* but not all its fixed pages.
        """
        # Get fixed pages with no image - ie not scanned.
        fixed_with_no_scan = FixedPage.objects.filter(paper=OuterRef("pk"), image=None)
        # Get fixed pages with image - ie scanned.
        fixed_with_scan = FixedPage.objects.filter(
            paper=OuterRef("pk"), image__isnull=False
        )
        # Get papers with some but not all scanned fixed pages
        some_but_not_all_fixed_present = Paper.objects.filter(
            Exists(fixed_with_no_scan), Exists(fixed_with_scan)
        )

        return some_but_not_all_fixed_present.count()

    @transaction.atomic
    def get_number_unused_test_papers(self) -> int:
        """Return the number of test-papers that are usused.

        A paper is unused when it has no fixed page images nor any mobile pages.
        """
        # Get fixed pages with image - ie scanned.
        fixed_with_scan = FixedPage.objects.filter(
            paper=OuterRef("pk"), image__isnull=False
        )
        # Get papers with neither fixed-with-scan nor mobile-pages
        no_images_at_all = Paper.objects.filter(
            ~Exists(fixed_with_scan), mobilepage__isnull=True
        )

        return no_images_at_all.count()

    @transaction.atomic
    def get_all_unused_test_papers(self) -> list[int]:
        """Return a list of paper-numbers of all unused test-papers. Is sorted into paper-number order.

        A paper is unused when it has no fixed page images nor any mobile pages.
        """
        # Get fixed pages with image - ie scanned.
        fixed_with_scan = FixedPage.objects.filter(
            paper=OuterRef("pk"), image__isnull=False
        )
        # Get papers with neither fixed-with-scan nor mobile-pages
        no_images_at_all = Paper.objects.filter(
            ~Exists(fixed_with_scan), mobilepage__isnull=True
        )
        return sorted([paper.paper_number for paper in no_images_at_all])

    @transaction.atomic
    def get_all_used_test_papers(self) -> list[int]:
        """Return a list of paper-numbers of all used test-papers. Is sorted into paper-number order.

        A paper is used when it has at least one fixed page image or any mobile page.
        """
        # Get fixed pages with image - ie scanned.
        fixed_with_scan = FixedPage.objects.filter(
            paper=OuterRef("pk"), image__isnull=False
        )
        has_mobile_page = MobilePage.objects.filter(paper=OuterRef("pk"))
        has_some_image = Paper.objects.filter(
            Exists(fixed_with_scan)
        ) | Paper.objects.filter(Exists(has_mobile_page))

        return sorted([paper.paper_number for paper in has_some_image])

    @transaction.atomic
    def get_page_image(self, test_paper: int, index: int) -> Image:
        """Return a page-image.

        Args:
            test_paper (int): paper ID
            index (int): page number
        """
        paper = Paper.objects.get(paper_number=test_paper)
        page = FixedPage.objects.get(paper=paper, page_number=index)
        return page.image

    def get_number_pushed_bundles(self) -> int:
        """Return the number of pushed bundles."""
        return Bundle.objects.all().count()

    def get_number_unpushed_bundles(self) -> int:
        """Return the number of uploaded, but not yet pushed, bundles."""
        return StagingBundle.objects.filter(pushed=False).count()

    @transaction.atomic
    def get_pushed_bundles_list(self) -> list[dict[str, Any]]:
        """Return a list of all pushed bundles."""
        bundle_list = []
        for bundle in Bundle.objects.all().prefetch_related(
            "staging_bundle", "user", "staging_bundle__user"
        ):
            bundle_list.append(
                {
                    "id": bundle.pk,
                    "name": bundle.staging_bundle.slug,
                    "pages": Image.objects.filter(bundle=bundle).count(),
                    "when_pushed": arrow.get(bundle.time_of_last_update).humanize(),
                    "when_uploaded": arrow.get(
                        bundle.staging_bundle.time_of_last_update
                    ).humanize(),
                    "who_pushed": bundle.user.username,
                    "who_uploaded": bundle.staging_bundle.user.username,
                }
            )
        return bundle_list

    def get_pushed_image(self, img_pk: int) -> Image | None:
        try:
            return Image.objects.get(pk=img_pk)
        except Image.DoesNotExist:
            return None

    @transaction.atomic
    def get_pushed_image_page_info(self, img_pk: int) -> dict[str, Any]:
        try:
            img = Image.objects.get(pk=img_pk)
        except Image.DoesNotExist:
            raise ValueError(f"Cannot find an image with pk {img_pk}.")

        if img.fixedpage_set.exists():  # linked by foreign key
            fp_obj = FixedPage.objects.get(image=img)
            return {
                "page_type": "fixed",
                "paper_number": fp_obj.paper.paper_number,
                "page_number": fp_obj.page_number,
                "bundle_name": img.bundle.name,
                "bundle_order": img.bundle_order,
            }
        elif img.mobilepage_set.exists():  # linked by foreign key
            # check the first such mobile page to get the paper_number
            paper_number = (
                MobilePage.objects.filter(image=img).first().paper.paper_number
            )
            q_idx_list = [
                mp_obj.question_index for mp_obj in MobilePage.objects.filter(image=img)
            ]
            _render = SpecificationService.render_html_flat_question_label_list
            return {
                "page_type": "mobile",
                "paper_number": paper_number,
                "question_index_list": q_idx_list,
                "question_list_html": _render(q_idx_list),
                "bundle_name": img.bundle.name,
                "bundle_order": img.bundle_order,
            }
        elif img.discardpage:  # linked by one-to-one
            return {
                "page_type": "discard",
                "reason": img.discardpage.discard_reason,
                "bundle_name": img.bundle.name,
                "bundle_order": img.bundle_order,
            }
        else:
            raise ValueError(
                f"Cannot determine what sort of page image {img_pk} is attached to."
            )

    @transaction.atomic
    def get_discarded_images(self) -> list[dict[str, Any]]:
        discards = []

        for img in (
            Image.objects.filter(discardpage__isnull=False)
            .prefetch_related("discardpage", "bundle", "bundle__staging_bundle")
            .order_by("bundle", "bundle_order")
        ):
            discards.append(
                {
                    "image": img.pk,
                    "reason": img.discardpage.discard_reason,
                    "bundle_pk": img.bundle.pk,
                    "bundle_name": img.bundle.staging_bundle.slug,
                    "order": img.bundle_order,
                    "discard_pk": img.discardpage.pk,
                }
            )

        return discards

    @transaction.atomic
    def get_pages_images_in_paper(self, paper_number: int) -> list[dict[str, Any]]:
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
        for fp_obj in paper_obj.fixedpage_set.all().order_by("page_number"):
            dat = {
                "page_type": "fixed",
                "page_number": fp_obj.page_number,
                "page_pk": fp_obj.pk,
            }
            if fp_obj.image:
                dat.update({"image": fp_obj.image.pk})
            else:
                dat.update({"image": None})
            page_images.append(dat)
        for mp_obj in paper_obj.mobilepage_set.all().order_by("question_index"):
            dat = {
                "page_type": "mobile",
                "question_number": mp_obj.question_index,
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
