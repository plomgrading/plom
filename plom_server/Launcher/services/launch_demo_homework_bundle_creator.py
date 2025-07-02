# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023-2025 Colin B. Macdonald
# Copyright (C) 2023 Edith Coates
# Copyright (C) 2023-2024 Andrew Rechnitzer

import subprocess
from pathlib import Path
from time import sleep

import pymupdf


class DemoHWBundleCreationService:
    """Handle creating homework bundles in the demo."""

    def make_hw_bundle(self, bundle: dict):
        """Construct a hw bundle pdf for use with demo."""
        paper_number = bundle["paper_number"]

        # Perhaps "pages" is not a very semantic name but this data is a list
        # of lists eg [[1], [1,2], [], [2,3]] representing an implicit mapping
        # from page (outer list index + 1) to a list of question indices
        question_idx_lists = bundle["pages"]

        print(
            f"Making a homework bundle as paper {paper_number}"
            f" with question-page mapping {question_idx_lists}"
        )

        out_file = Path(f"fake_hw_bundle_{paper_number}.pdf")
        doc = pymupdf.Document()
        for i, ql in enumerate(question_idx_lists):
            pg = i + 1
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

            bundle_name = f"fake_hw_bundle_{paper_number}"
            print(f"Scraping bundle id from bundle {bundle_name}...")
            # we need the bundle id: annoying to have to scrape it
            output = subprocess.check_output(
                ["python3", "-m", "plom.cli", "list-bundles"]
            )
            output = output.decode()
            for l in output.splitlines():
                if l.startswith(bundle_name):
                    bundle_id = int(l.split()[1])

            for i, qidx_list in enumerate(bundle["pages"]):
                pg = i + 1
                print(
                    f"Bundle {bundle_name} id {bundle_id} page {pg} "
                    f"to paper {paper_number} question indices {qidx_list}"
                )
                cmd = [
                    "python3",
                    "-m",
                    "plom.cli",
                    "map",
                    str(bundle_id),
                    str(pg),
                    "-t",
                    str(paper_number),
                    "-q",
                    str(qidx_list),
                ]
                print("Running command: " + " ".join(cmd))
                subprocess.run(cmd, check=True)
            sleep(0.25)
