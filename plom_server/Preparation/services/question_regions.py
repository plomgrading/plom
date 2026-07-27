# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Colin B. Macdonald

from typing import Any

from plom_server.Base.services import Settings
from plom_server.Papers.services import SpecificationService


class QuestionRegionsService:
    """Configure question regions."""

    @staticmethod
    def reset_question_regions() -> None:
        regions = []
        Settings.key_value_store_set("question_regions", regions)

    @classmethod
    def get_question_regions(cls) -> list[dict[str, Any]]:
        # perhaps in DB someday but for now use the general key-value store
        regions = Settings.key_value_store_get_or_none("question_regions")

        if regions is None:
            cls.reset_question_regions()
            regions = Settings.key_value_store_get_or_none("question_regions")
        return regions

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
    def subdivide_page(cls, pagenum: int, version: int, div: list[float]) -> None:
        """Convenience function to subdivide a page amongst the questions that share it.

        Args:
            pagenum: which page, indexed from 1.
            version: which version.
            div: a list of the interior divisions of a page, for example
                ``[0.4]`` or ``[0.33, 0.66]``.
        """
        # TODO: doc how this fails if no spec
        # spec = SpecificationService.get_the_spec()

        question_pages = SpecificationService.get_question_pages()

        # the question indices that share this page
        qindices = [k for k, v in question_pages.items() if pagenum in v]

        assert len(div) == len(qindices) - 1
        div = [0, *div, 100]

        regions = cls.get_question_regions()

        m = SpecificationService.get_question_labels_str_and_html_map()

        for i, qidx in enumerate(qindices):
            # TODO: someday will need to think about multiple pages per question...
            overlap = 0.02
            top = (div[i] / 100.0) - overlap
            bottom = (div[i + 1] / 100.0) + overlap
            top = max(0, top)
            bottom = min(1, bottom)
            height = bottom - top
            qlabel_str, qlabel_html = m[qidx]
            # TODO: need to deal with overwriting, when data exists already?
            regions.append(
                {
                    "qidx": qidx,
                    "qlabel": qlabel_str,
                    "qlabel_html": qlabel_html,
                    "version": version,
                    "page": pagenum,
                    "rect": [0, top, 1, height],
                }
            )
        Settings.key_value_store_set("question_regions", regions)
