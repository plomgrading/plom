# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2022-2023 Colin B. Macdonald

from typing import Any, Dict

from . import TestSpecService
from . import ReferencePDFService


class TestSpecProgressService:
    """Keep track of which parts of the test specification wizard have been completed."""

    def __init__(self, spec_service: TestSpecService):
        self.spec = spec_service

    def is_names_completed(self) -> bool:
        """Return True if the first page of the wizard has been completed."""
        has_long_name = False
        has_short_name = False
        has_n_versions = False

        if self.spec.get_long_name() != "":
            has_long_name = True

        if self.spec.get_short_name() != "":
            has_short_name = True

        if self.spec.get_n_versions() > 0:
            has_n_versions = True

        return has_short_name and has_long_name and has_n_versions

    def is_pdf_page_completed(self) -> bool:
        """Return True if the second page of the wizard has been completed."""
        ref_service = ReferencePDFService()
        try:
            pdf = ref_service.get_pdf()
            has_reference_pdf = True
        except RuntimeError:
            has_reference_pdf = False

        return has_reference_pdf

    def is_id_page_completed(self) -> bool:
        """Return True if the third page of the wizard has been completed."""
        id_page = self.spec.get_id_page_number()
        return id_page is not None

    def is_question_page_completed(self) -> bool:
        """Return True if the fourth page of the wizard has been completed."""
        n_questions = self.spec.get_n_questions()
        total_marks = self.spec.get_total_marks()
        return n_questions > 0 and total_marks > 0

    def is_question_detail_page_completed(self, index) -> bool:
        """Return True if a given question detail page has been completed."""
        if index not in self.spec.questions:
            return False

        question = self.spec.questions[index]
        return question.is_question_completed()

    def are_all_questions_completed(self) -> bool:
        """Return True if all the question detail pages have been completed."""
        n_questions = self.spec.get_n_questions()
        for i in range(n_questions):
            if not self.is_question_detail_page_completed(i):
                return False
        return True

    def is_dnm_page_completed(self) -> bool:
        """Return True if the do-not-mark page has been submitted."""
        return self.spec.specification().dnm_page_submitted

    def is_validate_page_completed(self) -> bool:
        the_spec = self.spec.specification()
        return the_spec.validate_page_submitted

    def get_progress_dict(self) -> Dict[str, Any]:
        """Return a dictionary with completion data for the wizard."""
        progress_dict: Dict[str, Any] = {}
        progress_dict["names"] = self.is_names_completed()
        progress_dict["upload"] = self.is_pdf_page_completed()
        progress_dict["id_page"] = self.is_id_page_completed()
        progress_dict["questions_page"] = self.is_question_page_completed()
        progress_dict["question_list"] = [
            self.is_question_detail_page_completed(i + 1)
            for i in range(self.spec.get_n_questions())
        ]
        progress_dict["dnm_page"] = self.is_dnm_page_completed()
        progress_dict["validate"] = self.is_validate_page_completed()

        return progress_dict

    def is_everything_complete(self) -> bool:
        """Return false if any item in the progress dict is false - otherwise, every part of the wizard is complete, so return true."""
        progress_dict = self.get_progress_dict()

        for key, value in progress_dict.items():
            if key == "question_list":
                for q in value:
                    if not q:
                        return False
            elif not value:
                return False

        return True

    def is_anything_complete(self) -> bool:
        """Return true if any of the wizard pages are completed, false otherwise."""
        progress_dict = self.get_progress_dict()
        vals = progress_dict.values()
        return True in vals
