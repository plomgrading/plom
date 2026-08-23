# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Colin B. Macdonald

from typing import Any, Sequence

from plom_server.Base.services import Settings
from plom_server.Papers.services import SpecificationService


class QuestionRegionsService:
    """Configure question regions."""

    @staticmethod
    def reset_question_regions() -> None:
        Settings.key_value_store_set("question_regions", [])

    @classmethod
    def get_question_regions(cls) -> list[dict[str, Any]]:
        # perhaps in DB someday but for now use the general key-value store
        regions = Settings.key_value_store_get_or_none("question_regions")

        if regions is None:
            cls.reset_question_regions()
            regions = Settings.key_value_store_get_or_none("question_regions")
        return regions

    @classmethod
    def set_question_regions(
        cls,
        qidx: int,
        pagenum: int | None,
        rect: Sequence[float | int],
        *,
        version: int | None = None,
    ) -> None:
        """Set the region for a particular question to subset of a page, optionally with a version.

        TODO: sanitize the qidx/pagenum makes sense!

        Args:
            qidx: which question, indexed from 1.
            pagenum: which page number, indexed from 1.  Or None and
                we'll try to find it, which will only work if the
                question does not span pages.
            rect: four floats of the form ``xmin, ymin, xmax, ymax``,
                each in the range [0, 1].

        Keyword Args:
            version: optionally, make the region version-specific.

        Exceptions:
            ObjectDoesNotExist: no such question index, typically b/c there is no spec.
            ValueError: question spans multiple pages but pagenum not specified.
        """
        pages = SpecificationService.get_question_pages()[qidx]
        if pagenum is None:
            if len(pages) == 1:
                pagenum = pages[0]
            else:
                raise ValueError(
                    f'Question idx {qidx} spans {pages} but "page" was not specified'
                )
        else:
            if pagenum not in pages:
                raise ValueError(f"Question idx {qidx} does not include page {pagenum}")

        cls._remove_question_regions(qidx, pagenum, version=version)
        regions = cls.get_question_regions()
        qlabel, qlabel_html = SpecificationService.get_question_label_str_and_html(qidx)
        regions.append(
            {
                "qidx": qidx,
                "qlabel": qlabel,
                "qlabel_html": qlabel_html,
                "version": version,
                "page": pagenum,
                "rect": rect,
            }
        )
        Settings.key_value_store_set("question_regions", regions)

    @classmethod
    def _remove_question_regions(
        cls, qidx: int, pagenum: int, *, version: int | None = None
    ) -> None:
        regions = cls.get_question_regions()
        for r in regions:
            if r["qidx"] == qidx and r["page"] == pagenum:
                if version is None:
                    regions.remove(r)
                else:
                    if r["version"] == version or r["version"] is None:
                        regions.remove(r)
        Settings.key_value_store_set("question_regions", regions)

    @staticmethod
    def get_shared_pages() -> list[dict[str, Any]]:
        """Produce a list pages that are shared by one or more questions."""
        question_pages = SpecificationService.get_question_pages()
        qidx_labels = SpecificationService.get_question_html_label_triples()

        info = []
        for pg in range(1, 1 + SpecificationService.get_n_pages()):
            # the question indices that share this page
            qindices = [k for k, v in question_pages.items() if pg in v]
            if len(qindices) > 1:
                qlabels = [b for (a, b, c) in qidx_labels if a in qindices]
                qlabels_html = [c for (a, b, c) in qidx_labels if a in qindices]
                info.append(
                    {
                        "page": pg,
                        "question_indicies_that_share": qindices,
                        "question_labels_that_share": qlabels,
                        "question_labels_that_share_html": qlabels_html,
                    }
                )
        return info

    @classmethod
    def get_region_info_per_page(cls) -> list:
        """Information about regions in a list of dicts, one per page."""
        question_pages = SpecificationService.get_question_pages()
        qidx_labels = SpecificationService.get_question_html_label_triples()

        regions = cls.get_question_regions()

        info = []
        for pg in range(1, 1 + SpecificationService.get_n_pages()):
            # the question indices that share this page
            qindices = [k for k, v in question_pages.items() if pg in v]
            qlabels_str = [b for (a, b, c) in qidx_labels if a in qindices]
            qlabels_html = [c for (a, b, c) in qidx_labels if a in qindices]

            if len(qindices) > 1:
                questions_share_this_page = True
            else:
                questions_share_this_page = False

            if any([r["page"] == pg for r in regions]):
                has_regions = True
                # TODO: sort explicitly by qidx?
                _page_regions = [r.copy() for r in regions if r["page"] == pg]
                page_region_rects = []
                for row in _page_regions:
                    # TODO: hacking out some None stuff that confuses javascript
                    row.pop("version")
                    page_region_rects.append(row["rect"])
            else:
                has_regions = False
                page_region_rects = []

            info.append(
                {
                    "page": pg,
                    "has_regions": has_regions,
                    "questions_share_this_page": questions_share_this_page,
                    "question_indicies": qindices,
                    # This one is for JS, TODO: caution about JS vs HTML escaping...!
                    "question_labels_str_list": qlabels_str,
                    # This one is for HTML
                    "question_labels_comma_sep_list_html": ", ".join(qlabels_html),
                    "page_region_rects": page_region_rects,
                    # Used to link html and js
                    "ref_image_html_id": f"reference_image_id_pg{pg}",
                    "canvas_html_id": f"canvas_id_pg{pg}",
                }
            )
        return info

    @classmethod
    def subdivide_page(
        cls,
        pagenum: int,
        div: list[float],
        *,
        version: int | None = None,
    ) -> None:
        """Convenience function to subdivide a page amongst the questions that share it.

        Args:
            pagenum: which page, indexed from 1.
            div: a list of the interior divisions of a page, for example
                ``[40]`` or ``[33, 66.2]``.

        Keyword Args:
            version: optionally do this subdivision for this version only.

        Raises:
            ValueError: number of divisions does not correspond to
                questions, is mis-sorted, out of range, etc.
            ObjectDoesNotExist: no spec yet.
        """
        question_pages = SpecificationService.get_question_pages()

        # the question indices that share this page
        qindices = [k for k, v in question_pages.items() if pagenum in v]

        if len(div) != len(qindices) - 1:
            raise ValueError(
                f"Page {pagenum} is shared by {len(qindices)} questions:"
                f" wrong number of divisions provided: {len(div)}"
                f" but the expected number is {len(qindices) - 1}"
            )
        if sorted(div) != div:
            raise ValueError("Divisions must be monotonic")
        for d in div:
            if not 0 < d < 100:
                raise ValueError(f'Division "{d}" out of range')

        div = [0, *div, 100]

        for i, qidx in enumerate(qindices):
            # TODO: someday will need to think about multiple pages per question...
            overlap = 0.02
            top = (div[i] / 100.0) - overlap
            bottom = (div[i + 1] / 100.0) + overlap
            top = max(0, top)
            bottom = min(1, bottom)
            QuestionRegionsService.set_question_regions(
                qidx, pagenum, [0, top, 1, bottom], version=version
            )
