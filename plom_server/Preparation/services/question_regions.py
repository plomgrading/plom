# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Colin B. Macdonald

import base64
from typing import Any

from plom_server.Base.services import Settings
from plom_server.Papers.services import SpecificationService
from .mocker import ExamMockerService


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
        cls, qidx: int, pagenum: int, rect, *, version: int | None = None
    ) -> None:
        """Set the crop region of a particular question to page, optionally with a version."""
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
        # TODO: doc how this fails if no spec
        # spec = SpecificationService.get_the_spec()

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
    def get_region_mockups(cls) -> list:
        question_pages = SpecificationService.get_question_pages()
        qidx_labels = SpecificationService.get_question_html_label_triples()

        regions = cls.get_question_regions()

        info = []
        for pg in range(1, 1 + SpecificationService.get_n_pages()):
            # the question indices that share this page
            qindices = [k for k, v in question_pages.items() if pg in v]
            qlabels = [b for (a, b, c) in qidx_labels if a in qindices]
            qlabels_html = [c for (a, b, c) in qidx_labels if a in qindices]
            if any([r["page"] == pg for r in regions]):
                has_regions = True
                # TODO: sort by qidx?
                _page_regions = [r.copy() for r in regions if r["page"] == pg]
                page_region_rects = []
                page_region_labels = []
                for row in _page_regions:
                    # TODO: hacking out some None stuff that confuses javascript
                    row.pop("version")
                    page_region_rects.append(row["rect"])
                    page_region_labels.append(row["qlabel_html"])
                # TODO: version hardcoded to 1
                png_bytes = ExamMockerService.get_temp_rendered_regions_page(
                    pg, 1, regions
                )
                png_as_string = base64.b64encode(png_bytes).decode("ascii")
            else:
                has_regions = False
                png_as_string = ""
            if has_regions:
                info.append(
                    {
                        "page": pg,
                        "question_indicies": qindices,
                        "question_labels": qlabels,
                        "question_labels_html": qlabels_html,
                        "has_regions": has_regions,
                        "page_region_image": png_as_string,
                        "page_region_rects": page_region_rects,
                        "page_region_labels": page_region_labels,
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
                ``[0.4]`` or ``[0.33, 0.66]``.

        Keyword Args:
            version: optionally do this subdivision for this version only.

        Raises:
            ValueError: number of divisions does not correspond to questions.
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
        div = [0, *div, 100]

        for i, qidx in enumerate(qindices):
            # TODO: someday will need to think about multiple pages per question...
            overlap = 0.02
            top = (div[i] / 100.0) - overlap
            bottom = (div[i + 1] / 100.0) + overlap
            top = max(0, top)
            bottom = min(1, bottom)
            height = bottom - top
            QuestionRegionsService.set_question_regions(
                qidx, pagenum, [0, top, 1, height], version=version
            )
