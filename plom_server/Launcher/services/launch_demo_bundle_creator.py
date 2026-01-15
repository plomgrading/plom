# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023-2026 Colin B. Macdonald
# Copyright (C) 2023 Edith Coates
# Copyright (C) 2023 Natalie Balashov
# Copyright (C) 2023-2025 Andrew Rechnitzer
# Copyright (C) 2024 Bryan Tanady

from collections import defaultdict
import csv
from pathlib import Path
import shutil
import tempfile
from typing import Any

import pymupdf

from django.core.management import call_command
from django.conf import settings

from plom.create import create_QR_codes, create_invalid_QR_and_bar_codes
from plom.create.scribble_utils import (
    scribble_name_and_id,
    scribble_pages,
    scribble_answer_in_box,
)
from plom.scan import pdfmucker

# TODO: was this somehow not supposed to import plom_server? why not?
# TODO: it seems it used to go to a lot of trouble not too.
from plom_server.Base.services import Settings
from plom_server.Papers.services import SpecificationService


class DemoBundleCreationService:
    """Handle generating demo bundles."""

    def get_classlist_as_dict(self) -> list[dict[str, Any]]:
        """Download the classlist and return as a list of dicts."""
        with tempfile.TemporaryDirectory() as td:
            classlist_file = Path(td) / "classlist.csv"
            classlist = []
            call_command("plom_preparation_classlist", "download", f"{classlist_file}")
            with open(classlist_file) as fh:
                red = csv.DictReader(fh, skipinitialspace=True)
                for row in red:
                    classlist.append(
                        {
                            "id": row["id"],
                            "name": row["name"],
                            "paper_number": row["paper_number"],
                        }
                    )
        return classlist

    def _get_extra_page_copy(self, dest_dir: Path) -> Path:
        """Get a copy of the extra-page pdf to the specified directory."""
        # Assumes that the extra page has been generated
        # and that we have local file system access to copy it
        shutil.copy2(
            (settings.MEDIA_ROOT / "non_db_files") / "extra_page.pdf",
            dest_dir,
        )
        return dest_dir / "extra_page.pdf"

    def _get_scrap_paper_copy(self, dest_dir: Path) -> Path:
        """Get a copy of the scrap-paper pdf to the specified directory."""
        # Assumes that the scrap paper has been generated
        # and that we have local file system access to copy it
        shutil.copy2(
            (settings.MEDIA_ROOT / "non_db_files") / "scrap_paper.pdf",
            dest_dir,
        )
        return dest_dir / "scrap_paper.pdf"

    def assign_students_to_papers(self, paper_list, classlist) -> list[dict]:
        """Map papers to names and IDs from the classlist, skipping any prenamed ones."""
        # prenamed papers are "exam_XXXX_YYYYYYY" and normal are "exam_XXXX"
        id_to_name = {X["id"]: X["name"] for X in classlist}
        sids_not_in_prename = [
            row["id"] for row in classlist if row["paper_number"] == ""
        ]

        assignment = []

        for path in paper_list:
            paper_number = path.stem.split("_")[1]
            if len(path.stem.split("_")) == 3:  # paper is prenamed
                sid = path.stem.split("_")[2]
                assignment.append(
                    {
                        "path": path,
                        "id": sid,
                        "name": id_to_name[sid],
                        "prenamed": True,
                        "paper_number": paper_number,
                    }
                )
            else:
                sid = sids_not_in_prename.pop(0)

                assignment.append(
                    {
                        "path": path,
                        "id": sid,
                        "name": id_to_name[sid],
                        "prenamed": False,
                        "paper_number": paper_number,
                    }
                )

        return assignment

    def make_last_page_with_wrong_version(
        self, pdf_doc: pymupdf.Document, paper_number: int
    ) -> None:
        """Muck around with the last page for testing purposes.

        Removes the last page of the doc and replaces it with a nearly
        blank page that contains a qr-code that is nearly valid except
        that the version is wrong.

        Args:
            pdf_doc: a pdf document of a test-paper.
            paper_number: the paper_number of that test-paper.

        Returns:
            None, but modifies ``pdf_doc``  as a side effect.
        """
        public_code = Settings.get_public_code()
        if not public_code:
            public_code = ""
        max_ver = SpecificationService.get_n_versions()
        with tempfile.TemporaryDirectory() as td:
            # take last page of paper and insert a qr-code from the page before that.
            page_number = pdf_doc.page_count
            # make a qr-code for this paper/page but with version max+1
            qr_pngs = create_QR_codes(
                paper_number, page_number, max_ver + 1, public_code, Path(td)
            )
            pdf_doc.delete_page()  # this defaults to the last page.

            pdf_doc.new_page(-1, *Settings.get_paper_size_in_pts())

            pdf_doc[-1].insert_text(
                (120, 60),
                text="This is a page has a qr-code with the wrong version",
                fontsize=18,
                color=[0, 0.75, 0.75],
            )
            qr_size = settings.PLOM_QR_CODE_SIZE
            # hard-code one qr-code in top-left
            rect = pymupdf.Rect(50, 50, 50 + qr_size, 50 + qr_size)
            pdf_doc[-1].insert_image(
                rect, pixmap=pymupdf.Pixmap(qr_pngs[1]), overlay=True
            )

    def append_extra_page(self, pdf_doc, paper_number, student_id, extra_page_path):
        """Append a simulated extra page to the pdf from the given student.

        Students frequently require extra paper during tests and the included page
        should be automatically marked as 'extra paper' by plom at bundle upload.
        A scanner-user then needs to enter the details (which are stamped on the
        page by this function).
        """
        with pymupdf.open(extra_page_path) as extra_pages_pdf:
            pdf_doc.insert_pdf(
                extra_pages_pdf,
                from_page=0,
                to_page=1,
                start_at=-1,
            )
            page_rect = pdf_doc[-1].rect
            # stamp some info on it - TODO - make this look better.
            tw = pymupdf.TextWriter(page_rect, color=(0, 0, 1))
            # TODO - make these numbers less magical
            maxbox = pymupdf.Rect(25, 400, 500, 600)
            # page.draw_rect(maxbox, color=(1, 0, 0))
            excess = tw.fill_textbox(
                maxbox,
                f"EXTRA PAGE - t{paper_number} Q1 - {student_id}",
                align=pymupdf.TEXT_ALIGN_LEFT,
                fontsize=18,
                font=pymupdf.Font("helv"),
            )
            assert not excess, "Text didn't fit: is extra-page text too long?"
            tw.write_text(pdf_doc[-1])
            tw.write_text(pdf_doc[-2])

    def append_scrap_page(self, pdf_doc, paper_number, student_id, scrap_paper_path):
        """Appends a scrap-paper page to the pdf.

        This is to simulate a student including some of the 'scrap paper' in with
        their assessment and it being included in the bundle. This should then
        be automatically marked as 'discard' by plom-scan on upload.
        """
        with pymupdf.open(scrap_paper_path) as scrap_paper_pdf:
            pdf_doc.insert_pdf(
                scrap_paper_pdf,
                from_page=0,
                to_page=1,
                start_at=-1,
            )
            page_rect = pdf_doc[-1].rect
            # stamp some info on it - TODO - make this look better.
            tw = pymupdf.TextWriter(page_rect, color=(0, 0, 1))
            # TODO - make these numbers less magical
            maxbox = pymupdf.Rect(25, 400, 500, 600)
            # page.draw_rect(maxbox, color=(1, 0, 0))
            excess = tw.fill_textbox(
                maxbox,
                f"SCRAP PAPER DNM - t{paper_number} - {student_id}",
                align=pymupdf.TEXT_ALIGN_LEFT,
                fontsize=18,
                font=pymupdf.Font("helv"),
            )
            assert not excess, "Text didn't fit: is scrap-paper text too long?"
            tw.write_text(pdf_doc[-1])
            tw.write_text(pdf_doc[-2])

    def append_duplicate_page(self, pdf_doc: pymupdf.Document) -> None:
        """Makes a (deep) copy of the last page of the PDF and appends it.

        This is to simulate sloppy scanning procedures in which a given
        page of the assessment might be scanned twice by accident.
        """
        last_page = len(pdf_doc) - 1
        pdf_doc.fullcopy_page(last_page)

    def insert_qr_from_previous_page(
        self, pdf_doc: pymupdf.Document, paper_number: int
    ) -> None:
        """Muck around with the penultimate page for testing purposes.

        Stamps a qr-code for the second-last page onto the last page,
        in order to create a page with inconsistent qr-codes. This can
        happen when, for example, a folded page is fed into the scanner.

        Args:
            pdf_doc: a pdf document of a test-paper.
            paper_number: the paper_number of that test-paper.

        Returns:
            None, but modifies ``pdf_doc`` as a side effect.
        """
        public_code = Settings.get_public_code()
        if not public_code:
            public_code = ""
        with tempfile.TemporaryDirectory() as td:
            # take last page of paper and insert a qr-code from the page before that.
            page_number = pdf_doc.page_count
            # make a qr-code for this paper, but for second-last page.
            qr_pngs = create_QR_codes(
                paper_number, page_number - 1, 1, public_code, Path(td)
            )
            pdf_doc[-1].insert_text(
                (120, 60),
                text="This is a page has a qr-code from the previous page",
                fontsize=18,
                color=[0, 0.75, 0.75],
            )
            # TODO: this function is never called, Issue #4127.
            qr_size = settings.PLOM_QR_CODE_SIZE
            # hard-code additional qr-code next to the top-left one
            rect = pymupdf.Rect(50, 50 + qr_size, 50 + qr_size, 50 + qr_size * 2)
            pdf_doc[-1].insert_image(
                rect, pixmap=pymupdf.Pixmap(qr_pngs[1]), overlay=True
            )

    def append_garbage_page(self, pdf_doc):
        """Append a 'garbage' page to the pdf.

        This is intended to simulate the scanner accidentally including
        a non-assessment page in their bundle (eg a shopping receipt).
        """
        pdf_doc.insert_page(
            -1, text="This is a garbage page", fontsize=18, color=[0, 0.75, 0]
        )

    def append_page_from_another_assessment(self, pdf_doc) -> None:
        """Append a (simulated) page from an assessment with a different public-code.

        This is intended to simulate the user accidentally uploading a page ffom a
        different assessment (as the developers may have done earlier in plom development).
        """
        public_code = Settings.get_public_code()
        # and make a new magic code that is not the same as the server's
        if public_code:
            assert len(public_code) == 6
        wrong_code = "000000"
        if wrong_code == public_code:
            wrong_code = "999999"

        with tempfile.TemporaryDirectory() as td:
            qr_pngs = create_QR_codes(1, 1, 1, wrong_code, Path(td))
            # now we have qr-code pngs that we can use to make a bogus page from a different assessment.
            # these are called "qr_0001_pg1_4.png" etc.
            pdf_doc.new_page(-1, *Settings.get_paper_size_in_pts())

            pdf_doc[-1].insert_text(
                (120, 60),
                text="This is a page from a different assessment",
                fontsize=18,
                color=[0, 0.75, 0.75],
            )
            qr_size = settings.PLOM_QR_CODE_SIZE
            # hard-code one qr-code in top-left
            rect = pymupdf.Rect(50, 50, 50 + qr_size, 50 + qr_size)
            # the 2nd qr-code goes in NW corner.
            pdf_doc[-1].insert_image(
                rect, pixmap=pymupdf.Pixmap(qr_pngs[1]), overlay=True
            )
            # (note don't care if even/odd page: is a new page, no staple indicator)

    def append_out_of_range_paper_and_page(self, pdf_doc) -> None:
        """Append two new pages to the pdf - one as test-1 page-999 and one as test-99999 page-1."""
        public_code = Settings.get_public_code()
        if not public_code:
            public_code = ""
        with tempfile.TemporaryDirectory() as td:
            qr_pngs = create_QR_codes(99999, 1, 1, public_code, Path(td))
            pdf_doc.new_page(-1, *Settings.get_paper_size_in_pts())
            pdf_doc[-1].insert_text(
                (120, 200),
                text="This is a page from a non-existent paper",
                fontsize=18,
                color=[0, 0.75, 0.75],
            )
            qr_size = settings.PLOM_QR_CODE_SIZE
            # hard-code one qr-code in top-left
            rect = pymupdf.Rect(50, 50, 50 + qr_size, 50 + qr_size)
            # the 2nd qr-code goes in NW corner.
            pdf_doc[-1].insert_image(
                rect, pixmap=pymupdf.Pixmap(qr_pngs[1]), overlay=True
            )

            qr_pngs = create_QR_codes(1, 999, 1, public_code, Path(td))
            pdf_doc.new_page(-1, *Settings.get_paper_size_in_pts())
            pdf_doc[-1].insert_text(
                (120, 200),
                text="This is a non-existent page from an existing test",
                fontsize=18,
                color=[0, 0.75, 0.75],
            )
            # hard-code one qr-code in top-left
            rect = pymupdf.Rect(50, 50, 50 + qr_size, 50 + qr_size)
            # the 2nd qr-code goes in NW corner.
            pdf_doc[-1].insert_image(
                rect, pixmap=pymupdf.Pixmap(qr_pngs[1]), overlay=True
            )

    def append_invalid_qr_code_pages(self, pdf_doc):
        """Append two garbage pages with mix of valid/invalid qr/bar-codes.

        More precisely
            * append a page with an invalid qr-code in top-left corner
            and two barcodes near middle of page, then
            * append a second page with a valid plom scrap paper qr-code
            in top-left corner and an invalid qr-code at top-right corner.

        This is intended to simulate the user accidentally uploading a page
        with non-plom qr codes on it (eg a supermarket receipt).
        """
        # a rather cludge way to get at the spec via commandline tools
        # really we just need the public code.
        with tempfile.TemporaryDirectory() as td:
            invalid_qr_bar_codes = create_invalid_QR_and_bar_codes(Path(td))
            # now we have a qr-code and 2 bar-codes which are not
            # valid for plom, and finally one valid scrap-paper code
            # for the top-left corner. The barcodes are 300-wide and 100-high
            pdf_doc.new_page(-1, *Settings.get_paper_size_in_pts())
            pdf_doc[-1].insert_text(
                (120, 60),
                text="This is a page with invalid qr-code and bar-codes",
                fontsize=18,
                color=[0, 0.75, 0.75],
            )
            qr_size = settings.PLOM_QR_CODE_SIZE
            # 0th item is the qr-code --- put it in the top-left corner
            rect = pymupdf.Rect(50, 50, 50 + qr_size, 50 + qr_size)
            pdf_doc[-1].insert_image(
                rect, pixmap=pymupdf.Pixmap(invalid_qr_bar_codes[0]), overlay=True
            )
            # the next two are barcodes - make them wider
            rect = pymupdf.Rect(100, 250, 400, 350)
            pdf_doc[-1].insert_image(
                rect, pixmap=pymupdf.Pixmap(invalid_qr_bar_codes[1]), overlay=True
            )
            rect = pymupdf.Rect(100, 400, 400, 500)
            pdf_doc[-1].insert_image(
                rect, pixmap=pymupdf.Pixmap(invalid_qr_bar_codes[2]), overlay=True
            )
            pdf_doc.new_page(-1, *Settings.get_paper_size_in_pts())
            w = pdf_doc[-1].rect.width
            pdf_doc[-1].insert_text(
                (120, 60),
                text="This is a page with 1 valid qr and 1 invalid qr",
                fontsize=18,
                color=[0, 0.75, 0.75],
            )
            rect = pymupdf.Rect(50, 50, 50 + qr_size, 50 + qr_size)
            pdf_doc[-1].insert_image(
                rect, pixmap=pymupdf.Pixmap(invalid_qr_bar_codes[3]), overlay=True
            )
            rect = pymupdf.Rect(w - 50 - qr_size, 50, w - 50, 50 + qr_size)
            pdf_doc[-1].insert_image(
                rect, pixmap=pymupdf.Pixmap(invalid_qr_bar_codes[0]), overlay=True
            )

    def _convert_duplicates_dict(self, duplicates):
        """If duplicates is a list of dicts, convert into a dict."""
        duplicates_dict = {}
        for paper_dict in duplicates:
            duplicates_dict[paper_dict["paper"]] = paper_dict["page"]
        return duplicates_dict

    def _convert_duplicates_list(self, duplicates):
        """If duplicates is a list, convert into a dict."""
        duplicates_dict = {}
        for paper in duplicates:
            duplicates_dict[paper] = -1
        return duplicates_dict

    def muck_paper(self, filepath: str, operation: str) -> None:
        """Muck a paper from the given filepath with the given operation.

        Args:
            filepath: path to the file to be mucked.
            operation: the type of muck operation to do.
        """
        second_to_last_page = pymupdf.open(filepath).page_count - 1
        corner = "bottom_left"

        severity = 0.8
        jaggedness = 2
        # cmd = f"python3 -m plom.scan.pdfmucker {filepath} {second_to_last_page} {operation} {corner} --severity={severity}"
        # subprocess.check_call(cmd.split())
        pdfmucker.muck_paper(
            filepath=filepath,
            page_number=second_to_last_page,
            operation=operation,
            corner=corner,
            severity=severity,
            jaggedness=jaggedness,
        )
        print("Mucking Operation: ", operation)

    def scribble_to_create_bundle(
        self,
        assigned_papers_ids: list[dict[str, Any]],
        extra_page_path: Path,
        scrap_paper_path: Path,
        out_file: Path,
        *,
        extra_page_papers: list = [],
        scrap_page_papers: list = [],
        garbage_page_papers: list = [],
        duplicate_pages: list[int] = [],
        duplicate_qr: list = [],
        wrong_version: list = [],
        wrong_assessment: list = [],
        out_of_range_papers: list = [],
        obscure_qr_papers: list = [],
        invalid_qr_papers: list = [],
        mucking_operation: list[str] = [],
        versioned_id: bool = False,
    ) -> None:
        """Scribble on some of the papers to create a bundle, along with various others inclusions.

        Args:
            assigned_papers_ids: Which paper numbers to use for this bundle.
            extra_page_path: where to find the template extra page.
            scrap_paper_path: where to find the template scrap paper.
            out_file: where to save the created PDF bundle.

        Keyword Args:
            extra_page_papers: list of paper_numbers to which we append
                a couple of extra pages.
            scrap_page_papers: list of paper_numbers to which we append
                a couple of scrap-paper pages.
            garbage_page_papers: list of paper_numbers to which we append
                a garbage page.
            duplicate_pages: list of papers to have their final page
                duplicated.
            duplicate_qr: TODO.
            out_of_range_papers: TODO.
            obscure_qr_papers: TODO.
            invalid_qr_papers: list of papers to which we append a
                final page stamped with invalid qr-code and bar-code.
            mucking_operation: a list of mucking operations to apply,
                simulating various sorts of damage to the pages.
            wrong_version: list of paper numbers to which we replace last
                page with a blank but wrong version number.
            wrong_assessment: list of paper numbers to which we append a
                page from a different assessment.
            versioned_id: whether or not using different versions of the id-page

        Returns:
            None.
        """
        if duplicate_qr:
            print(f"====: duplicate_qr={duplicate_qr}")
            print(assigned_papers_ids)
        with pymupdf.open() as all_pdf_documents:
            for paper in assigned_papers_ids:
                with pymupdf.open(paper["path"]) as pdf_document:
                    # first put an ID on paper if it is not prenamed.
                    paper_number = int(paper["paper_number"])

                    if not paper["prenamed"]:
                        # if using versioned id pages and paper_number is even, then
                        # we need to put the name/ID in non-standard position.
                        if versioned_id and (paper_number % 2 == 0):
                            # warning: magic number for position of ID box in version 2.
                            scribble_name_and_id(
                                pdf_document, paper["id"], paper["name"], y_offset=77
                            )
                            # TODO = when we stop supporting legacy plom this
                            # y_offset should become y_pos for each version
                            # of the id page in the demo.
                        else:
                            scribble_name_and_id(
                                pdf_document, paper["id"], paper["name"]
                            )

                    if paper_number in wrong_version:
                        self.make_last_page_with_wrong_version(
                            pdf_document, paper_number
                        )

                    if paper_number in extra_page_papers:
                        self.append_extra_page(
                            pdf_document,
                            paper["paper_number"],
                            paper["id"],
                            extra_page_path,
                        )
                    if paper_number in scrap_page_papers:
                        self.append_scrap_page(
                            pdf_document,
                            paper["paper_number"],
                            paper["id"],
                            scrap_paper_path,
                        )
                    if paper_number in duplicate_pages:
                        self.append_duplicate_page(pdf_document)

                    # scribble on the pages
                    scribble_pages(pdf_document)
                    # scribble in the answer boxes on p3 of the current demo
                    # magic numbers - need to be updated if demo assessment is changed
                    scribble_answer_in_box(pdf_document, 3, 0.62, 0.195)
                    scribble_answer_in_box(pdf_document, 3, 0.62, 0.455)
                    scribble_answer_in_box(pdf_document, 3, 0.62, 0.725)

                    if duplicate_qr:
                        print(f"DEBUG: {duplicate_qr}, paper_number={paper_number}")
                    # insert a qr-code from a previous page after scribbling
                    if paper_number in duplicate_qr:
                        print("* - " * 80)
                        print(paper_number)
                        self.insert_qr_from_previous_page(pdf_document, paper_number)

                    # append a garbage page after the scribbling
                    if paper_number in garbage_page_papers:
                        self.append_garbage_page(pdf_document)

                    # TODO: Append out-of-range papers and wrong public codes to some bundles
                    if paper_number in wrong_assessment:
                        self.append_page_from_another_assessment(pdf_document)
                    if paper_number in out_of_range_papers:
                        self.append_out_of_range_paper_and_page(pdf_document)
                    if paper_number in invalid_qr_papers:
                        self.append_invalid_qr_code_pages(pdf_document)

                    with tempfile.NamedTemporaryFile(
                        delete=True, suffix=".pdf"
                    ) as temp_pdf:
                        pdf_document.save(temp_pdf.name)
                        temp_pdf_path = temp_pdf.name
                        if paper_number in obscure_qr_papers:
                            operation = mucking_operation[0]
                            mucking_operation.pop(0)
                            self.muck_paper(temp_pdf_path, operation)
                            pdf_document = pymupdf.open(temp_pdf_path)

                    # finally, append this to the bundle
                    all_pdf_documents.insert_pdf(pdf_document)

            all_pdf_documents.save(out_file)

    def _flatten(self, list_to_flatten):
        flat_list = []
        for sublist in list_to_flatten:
            flat_list += sublist
        return flat_list

    def _get_combined_list(self, bundles: dict, key: str):
        filtered = filter(lambda bundle: key in bundle.keys(), bundles)
        return self._flatten([bundle[key] for bundle in filtered])

    def scribble_on_exams(self, config, *, versioned_id=False):
        """Add simulated student-annotations to the pages of papers.

        Note: Also, if dictated by the demo config, simulates poor
        scanning of physical papers.
        """
        bundles = config.bundles
        n_bundles = len(bundles)

        classlist = self.get_classlist_as_dict()
        classlist_length = len(classlist)
        papers_to_print = settings.MEDIA_ROOT / "papersToPrint"
        paper_list = [paper for paper in papers_to_print.glob("exam*.pdf")]
        extra_page_path = self._get_extra_page_copy(papers_to_print)
        scrap_paper_path = self._get_scrap_paper_copy(papers_to_print)

        number_papers_to_use = classlist_length
        papers_to_use = sorted(paper_list)[:number_papers_to_use]

        assigned_papers_ids = self.assign_students_to_papers(papers_to_use, classlist)
        number_prenamed = sum(1 for X in assigned_papers_ids if X["prenamed"])

        print("v" * 40)
        print(
            f"Making bundles from {len(papers_to_use)} papers, of which {number_prenamed} are prenamed"
        )
        for i in range(n_bundles):
            bundle = defaultdict(list, bundles[i])
            bundle_path = Path(f"fake_bundle{i + 1}.pdf")
            print(
                f'  - creating bundle "{bundle_path.name}" from papers '
                f"{bundle['first_paper']} to {bundle['last_paper']}"
            )
            first_idx = bundle["first_paper"] - 1
            last_idx = bundle["last_paper"]
            papers_in_bundle = assigned_papers_ids[first_idx:last_idx]

            self.scribble_to_create_bundle(
                papers_in_bundle,
                extra_page_path,
                scrap_paper_path,
                bundle_path,
                extra_page_papers=bundle["extra_page_papers"],
                scrap_page_papers=bundle["scrap_page_papers"],
                garbage_page_papers=bundle["garbage_page_papers"],
                duplicate_pages=bundle["duplicate_pages"],
                duplicate_qr=bundle["duplicate_qr_papers"],
                wrong_version=bundle["wrong_version_papers"],
                wrong_assessment=bundle["wrong_assessment_papers"],
                out_of_range_papers=bundle["out_of_range_papers"],
                obscure_qr_papers=bundle["obscure_qr_papers"],
                invalid_qr_papers=bundle["invalid_qr_papers"],
                mucking_operation=bundle["operations"],
                versioned_id=versioned_id,
            )

        for i in range(min(2, n_bundles)):
            bundle_path = Path(f"fake_bundle{i + 1}.pdf")
            # TODO: consider outsourcing this operation to the pdfmucker tool
            print(f"Reversing order and rotating pages of bundle {bundle_path}")
            d2 = pymupdf.open()
            with pymupdf.open(bundle_path) as doc:
                for i in range(len(doc) - 1, -1, -1):
                    d2.insert_pdf(doc, from_page=i, to_page=i)
            for pg in range(len(d2)):
                d2[pg].set_rotation(180)
            d2.ez_save(bundle_path)

        print("^" * 40)
