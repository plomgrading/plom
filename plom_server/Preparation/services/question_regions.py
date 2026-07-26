# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Colin B. Macdonald

from typing import Any

from plom_server.Base.services import Settings
from plom_server.Papers.services import SpecificationService


class QuestionRegionsService:
    """Configure question regions."""

    @staticmethod
    def reset_question_regions() -> None:
        # TODO: colin hates these string keys, but json...
        regions = {
            str(qidx): [] for qidx in SpecificationService.get_question_indices()
        }
        Settings.key_value_store_set("question_regions", regions)

    @classmethod
    def get_question_regions(cls) -> dict:
        # perhaps in DB someday but for now use the general key-value store
        regions = Settings.key_value_store_get_or_none("question_regions")

        if regions is None:
            cls.reset_question_regions()
            regions = Settings.key_value_store_get_or_none("question_regions")
        return regions

    @staticmethod
    def get_shared_pages() -> list[dict[str, Any]]:
        # TODO: doc how this fails if no spec
        # spec = SpecificationService.get_the_spec()

        question_pages = SpecificationService.get_question_pages()

        qidx_label_pairs = SpecificationService.get_question_index_label_pairs()

        info = []
        for pg in range(1, 1 + SpecificationService.get_n_pages()):
            # the question indices that share this page
            qindices = [k for k, v in question_pages.items() if pg in v]
            if len(qindices) > 1:
                qlabels = [b for (a, b) in qidx_label_pairs if a in qindices]
                info.append(
                    {
                        "page": pg,
                        "question_indicies_that_share": qindices,
                        "question_labels_that_share": qlabels,
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

        # meh = SpecificationService.get_question_index_label_pairs()
        # meh = [b for (a, b) in meh if a in qindices]
        # info = {"page": pg, "questions_that_share": meh}

        assert len(div) == len(qindices) - 1
        div = [0, *div, 100]

        regions = cls.get_question_regions()

        for i, qidx in enumerate(qindices):
            # TODO: or maybe append
            # TODO: someday will need to think about multiple pages per question...
            overlap = 0.02
            top = (div[i] / 100.0) - overlap
            bottom = (div[i + 1] / 100.0) + overlap
            top = max(0, top)
            bottom = min(1, bottom)
            height = bottom - top
            regions[str(qidx)] = [{"page": pagenum, "rect": [0, top, 1, height]}]
        Settings.key_value_store_set("question_regions", regions)
