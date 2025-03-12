# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2022 Brennen Chiu
# Copyright (C) 2023 Natalie Balashov
# Copyright (C) 2023 Julian Lapenna
# Copyright (C) 2023-2025 Andrew Rechnitzer
# Copyright (C) 2024-2025 Colin B. Macdonald

from typing import Any

from django.db import transaction
from django.db.models import Exists, OuterRef, Prefetch

from plom_server.Papers.models import (
    FixedPage,
    MobilePage,
    DiscardPage,
    Paper,
    Image,
    Bundle,
    IDPage,
    DNMPage,
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

    @staticmethod
    @transaction.atomic
    def get_all_complete_papers() -> dict[int, dict[str, list[dict[str, Any]]]]:
        """Dict of info about Papers that are completely scanned.

        A paper is complete when it either has **all** its fixed
        pages, or it has no fixed pages but has some extra-pages.

        Returns:
            Dict keyed by paper number and then for each we have keys
            "fixed" and "mobile".  Under each of those we have a list of
            dicts of key-value pairs about pages.  The information in
            "fixed" and "mobile" case is different, for example "mobile"
            have page labels and "fixed" do not.
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

        complete: dict[int, dict[str, list[dict[str, Any]]]] = {}
        for paper in all_fixed_present:
            complete[paper.paper_number] = {"fixed": [], "mobile": []}
            # notice we don't specify order or prefetch in the loops
            # below here because we did the hard work above
            for fp in paper.fixedpage_set.all():
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
                        "question_number": mp.question_index,
                        "img_pk": mp.image.pk,
                        "page_pk": mp.pk,
                        "page_label": (
                            f"qi.{mp.question_index}" if mp.question_index else "dnm"
                        ),
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
                        "page_pk": mp.pk,
                        "page_label": (
                            f"qi.{mp.question_index}" if mp.question_index else "dnm"
                        ),
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
                            "page_pk": fp.pk,
                            "img_pk": fp.image.pk,
                        }
                    )
                else:
                    if isinstance(fp, DNMPage):
                        kind = "DNMPage"
                    elif isinstance(fp, IDPage):
                        kind = "IDPage"
                    else:  # must be a question-page
                        kind = "QuestionPage"
                    incomplete[paper.paper_number]["fixed"].append(
                        {
                            "status": "missing",
                            "page_number": fp.page_number,
                            "page_pk": fp.pk,
                            "kind": kind,
                        }
                    )
                    del kind
            for mp in paper.mobilepage_set.all():
                incomplete[paper.paper_number]["mobile"].append(
                    {
                        "question_number": mp.question_index,
                        "img_pk": mp.image.pk,
                        "page_pk": mp.pk,
                        "page_label": (
                            f"qi.{mp.question_index}" if mp.question_index else "dnm"
                        ),
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
        """Return the number of pushed bundles (excluding system bundles)."""
        return Bundle.objects.filter(_is_system=False).count()

    def get_number_unpushed_bundles(self) -> int:
        """Return the number of uploaded, but not yet pushed, bundles."""
        return StagingBundle.objects.filter(pushed=False).count()

    def get_pushed_image(self, img_pk: int) -> Image | None:
        """Return a database Image object with the given pk or None if it does not exist."""
        try:
            return Image.objects.get(pk=img_pk)
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
            * page_number: the page_number of  the fixed page.
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
                "image_pk": None,
                "bundle_name": None,
                "bundle_order": None,
            }
        else:
            return {
                "page_type": "fixed",
                "paper_number": fp_obj.paper.paper_number,
                "page_number": fp_obj.page_number,
                "image_pk": fp_obj.image.pk,
                "bundle_name": fp_obj.image.bundle.name,
                "bundle_order": fp_obj.image.bundle_order,
            }

    @transaction.atomic
    def get_pushed_mobile_page_image_info(self, page_pk: int) -> dict[str, Any]:
        """Given the pk of the mobile-page return info about it and its image.

        Args:
            page_pk: the pk of the mobile-page.

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
        mp_obj = MobilePage.objects.get(pk=page_pk)
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
