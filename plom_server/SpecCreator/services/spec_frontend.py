# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2023 Colin B. Macdonald

import json
from typing import Any, Dict, List


class SpecCreatorFrontendService:
    """Handles passing data from the frontend to the staging test specification object, and vice versa."""

    def get_pages_for_id_select_page(self, pages) -> List[Dict[str, Any]]:
        """Return a list of pages, with an extra field representing the @click statement to pass to alpine.

        For the ID page.

        Args:
            pages: a list of dictionaries, passed from StagingSpecificationService.get_page_list

        Returns:
            List of page dictionaries.
        """
        for i in range(len(pages)):
            page = pages[i]
            if not page["dnm_page"] and not page["question_page"]:
                page["at_click"] = f"page{i}selected = !page{i}selected"
            else:
                page["at_click"] = ""
        return pages

    def get_id_page_alpine_xdata(self, pages) -> str:
        """Generate top-level x-data object for the ID page template.

        Args:
            pages: a list of dictionaries, passed from `StagingSpecificationService.get_page_list`.

        Returns:
            JSON object dump.
        """
        x_data = {}
        for i in range(len(pages)):
            page = pages[i]
            if page["id_page"]:
                x_data[f"page{i}selected"] = True
            else:
                x_data[f"page{i}selected"] = False

        return json.dumps(x_data)

    def get_pages_for_question_detail_page(
        self, pages, question_id: int
    ) -> List[Dict[str, Any]]:
        """Return a list of pages, with an extra field representing the @click statement to pass to alpine.

        For the question detail page.

        Args:
            pages: a list of dictionaries, passed from StagingSpecificationService.get_page_list
            question_id: The index of the question page

        Returns:
            List of page dictionaries.
        """
        for i in range(len(pages)):
            page = pages[i]
            if page["question_page"] == question_id:
                page["at_click"] = f"page{i}selected = !page{i}selected"
            elif page["question_page"]:
                page["at_click"] = ""
            elif page["dnm_page"] or page["id_page"]:
                page["at_click"] = ""
            else:
                page["at_click"] = f"page{i}selected = !page{i}selected"
        return pages

    def get_question_detail_page_alpine_xdata(self, pages, question_id: int) -> str:
        """Generate top-level x-data object for the question detail page template.

        Args:
            pages: a list of dictionaries, passed from StagingSpecificationService.pages
            question_id: question index

        Returns:
            JSON object dump.
        """
        x_data = {}
        for i in range(len(pages)):
            page = pages[i]
            if page["question_page"] == question_id:
                x_data[f"page{i}selected"] = True
            else:
                x_data[f"page{i}selected"] = False

        return json.dumps(x_data)

    def get_pages_for_dnm_select_page(self, pages) -> List[Dict[str, Any]]:
        """Return a list of pages, with an extra field representing the @click statement to pass to alpine.

        For the do-not-mark page.

        Args:
            pages: a list of dictionaries, passed from StagingSpecificationService.pages

        Returns:
            List of page dictionaries.
        """
        for i in range(len(pages)):
            page = pages[i]
            if not page["id_page"] and not page["question_page"]:
                page["at_click"] = f"page{i}selected = !page{i}selected"
            else:
                page["at_click"] = ""
        return pages

    def get_dnm_page_alpine_xdata(self, pages) -> str:
        """Generate top-level x-data object for the do not mark page template.

        Args:
            pages: a list of dictionaries, passed from StagingSpecificationService.pages

        Returns:
            JSON object dump.
        """
        x_data = {}
        for i in range(len(pages)):
            page = pages[i]
            if page["dnm_page"]:
                x_data[f"page{i}selected"] = True
            else:
                x_data[f"page{i}selected"] = False

        return json.dumps(x_data)
