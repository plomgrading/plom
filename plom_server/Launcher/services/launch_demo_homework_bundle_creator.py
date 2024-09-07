# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Colin B. Macdonald
# Copyright (C) 2023 Edith Coates
# Copyright (C) 2023-2024 Andrew Rechnitzer

import pymupdf as fitz
from pathlib import Path
from time import sleep

from django.core.management import call_command


class DemoHWBundleCreationService:
    """Handle creating homework bundles in the demo."""

    def make_hw_bundle(self, bundle: dict):
        """Construct a hw bundle pdf for use with demo."""
        paper_number = bundle["paper_number"]
        question_list = bundle["pages"]

        print(
            f"Making a homework bundle as paper {paper_number} with question-page mapping {question_list}"
        )

        # question_list should be a list of lists eg [[1], [1,2], [], [2,3]]
        out_file = Path(f"fake_hw_bundle_{paper_number}.pdf")
        doc = fitz.Document()
        pg = 0
        for ql in question_list:
            pg += 1
            doc.new_page(-1)
            if ql:
                txt = f"Paper.page {paper_number}.{pg}: contains info for question(s) {ql}"
            else:
                txt = f"Paper.page {paper_number}.{pg}: does not contain useful info - discard it!"
            doc[-1].insert_text(
                (120, 50),
                text=txt,
                fontsize=18,
                color=[0, 0.25, 0.25],
            )

        doc.save(out_file)

    def map_homework_pages(self, homework_bundles=[]):
        """Assign questions to the pages homework bundles."""
        print("Mapping homework pages to questions")
        for bundle in homework_bundles:
            paper_number = bundle["paper_number"]
            question_list = bundle["pages"]

            bundle_name = f"fake_hw_bundle_{paper_number}"
            print(
                f"Assigning pages in {bundle_name} to paper {paper_number} questions {question_list}"
            )
            call_command(
                "plom_paper_scan",
                "map",
                bundle_name,
                "-t",
                paper_number,
                "-q",
                str(question_list),
            )
            sleep(0.5)
