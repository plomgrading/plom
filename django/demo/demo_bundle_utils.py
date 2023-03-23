# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2023 Colin B. Macdonald
# Copyright (C) 2023 Edith Coates

import csv
import fitz
from pathlib import Path
import tempfile

from django.core.management import call_command

from plom.create.scribble_utils import (
    scribble_name_and_id,
    scribble_pages,
    splitFakeFile,
)

extra_page_font_size = 18


def get_classlist_as_dict():
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


def get_extra_page():
    # Assumes that the extra page has been generated
    call_command(
        "plom_preparation_extrapage", "download", "media/papersToPrint/extra_page.pdf"
    )


def assign_students_to_papers(paper_list, classlist):
    # prenamed papers are "exam_XXXX_YYYYYYY" and normal are "exam_XXXX"
    all_sid = [row["id"] for row in classlist]
    id_to_name = {X["id"]: X["name"] for X in classlist}

    assignment = []

    for path in paper_list:
        paper_number = path.stem.split("_")[1]
        if len(path.stem.split("_")) == 3:  # paper is prenamed
            sid = path.stem.split("_")[2]
            all_sid.remove(sid)
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
            sid = all_sid.pop(0)

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


def append_extra_page(pdf_doc, paper_number, student_id, extra_page_path):
    with fitz.open(extra_page_path) as extra_pages_pdf:
        pdf_doc.insert_pdf(
            extra_pages_pdf,
            from_page=0,
            to_page=1,
            start_at=-1,
        )
        page_rect = pdf_doc[-1].rect
        # stamp some info on it - TODO - make this look better.
        tw = fitz.TextWriter(page_rect, color=(0, 0, 1))
        # TODO - make these numbers less magical
        maxbox = fitz.Rect(25, 400, 500, 600)
        # page.draw_rect(maxbox, color=(1, 0, 0))
        excess = tw.fill_textbox(
            maxbox,
            f"EXTRA PAGE - t{paper_number} Q1 - {student_id}",
            align=fitz.TEXT_ALIGN_LEFT,
            fontsize=extra_page_font_size,
            font=fitz.Font("helv"),
        )
        assert not excess, "Text didn't fit: is extra-page text too long?"
        tw.write_text(pdf_doc[-1])
        tw.write_text(pdf_doc[-2])


def append_duplicate_page(pdf_doc, page_number):
    pdf_doc.fullcopy_page(page_number - 1)


def append_garbage_page(pdf_doc):
    pdf_doc.insert_page(
        -1, text="This is a garbage page", fontsize=18, color=[0, 0.75, 0]
    )


def insert_page_from_another_assessment(pdf_doc):
    from plom import SpecVerifier
    from plom.create.mergeAndCodePages import create_QR_codes

    # a rather cludge way to get at the spec via commandline tools
    # really we just need the public code.
    with tempfile.TemporaryDirectory() as td:
        spec_file = Path(td) / "the_spec.toml"
        call_command("plom_preparation_test_spec", "download", f"{spec_file}")
        spec = SpecVerifier.from_toml_file(spec_file).spec
        # now make a new magic code that is not the same as the spec
        if spec["publicCode"] == "00000":
            code = "99999"
        else:
            code = "00000"
        qr_pngs = create_QR_codes(1, 1, 1, code, Path(td))
        # now we have qr-code pngs that we can use to make a bogus page from a different assessment.
        # these are called "qr_0001_pg1_4.png" etc.
        pdf_doc.new_page(-1)
        pdf_doc[-1].insert_text(
            (120, 200),
            text="This is a page from a different assessment",
            fontsize=18,
            color=[0, 0.75, 0.75],
        )
        # hard-code one qr-code in top-left
        rect = fitz.Rect(50, 50, 50 + 70, 50 + 70)
        # the 2nd qr-code goes in NW corner.
        pdf_doc[-1].insert_image(rect, pixmap=fitz.Pixmap(qr_pngs[1]), overlay=True)
        # (note don't care if even/odd page: is a new page, no staple indicator)


def insert_qr_from_previous_page(pdf_doc, paper_number):
    """Stamps a qr-code for the second-last page onto the last page,
    in order to create a page with inconsistent qr-codes. This can
    happen when, for example, a folded page is fed into the scanner.


    Args: pdf_doc (fitz.Document): a pdf document of a test-paper.
          paper_number (int): the paper_number of that test-paper.

    Returns:
       pdf_doc (fitz.Document): the updated pdf-document with the inconsistent qr-codes on its last page.
    """
    from plom import SpecVerifier
    from plom.create.mergeAndCodePages import create_QR_codes

    # a rather cludge way to get at the spec via commandline tools
    # really we just need the public code.
    with tempfile.TemporaryDirectory() as td:
        spec_file = Path(td) / "the_spec.toml"
        call_command("plom_preparation_test_spec", "download", f"{spec_file}")
        code = SpecVerifier.from_toml_file(spec_file).spec["publicCode"]

        # take last page of paper and insert a qr-code from the page before that.
        page_number = pdf_doc.page_count
        # make a qr-code for this paper, but for second-last page.
        qr_pngs = create_QR_codes(paper_number, page_number - 1, 1, code, Path(td))
        pdf_doc[-1].insert_text(
            (120, 200),
            text="This is a page has a qr-code from the previous page",
            fontsize=18,
            color=[0, 0.75, 0.75],
        )
        # hard-code one qr-code in top-left
        rect = fitz.Rect(50, 50 + 70, 50 + 70, 50 + 70 * 2)
        pdf_doc[-1].insert_image(rect, pixmap=fitz.Pixmap(qr_pngs[1]), overlay=True)


def make_last_page_with_wrong_version(pdf_doc, paper_number):
    """Removes the last page of the doc and replaces it with a nearly
    blank page that contains a qr-code that is nearly valid except
    that the version is wrong.


    Args: pdf_doc (fitz.Document): a pdf document of a test-paper.
          paper_number (int): the paper_number of that test-paper.

    Returns:
       pdf_doc (fitz.Document): the updated pdf-document with replaced last page.

    """
    from plom import SpecVerifier
    from plom.create.mergeAndCodePages import create_QR_codes

    # a rather cludge way to get at the spec via commandline tools
    # really we just need the public code.
    with tempfile.TemporaryDirectory() as td:
        spec_file = Path(td) / "the_spec.toml"
        call_command("plom_preparation_test_spec", "download", f"{spec_file}")
        spec = SpecVerifier.from_toml_file(spec_file).spec
        code = spec["publicCode"]
        max_ver = spec["numberOfVersions"]

        # take last page of paper and insert a qr-code from the page before that.
        page_number = pdf_doc.page_count
        # make a qr-code for this paper/page but with version max+1
        qr_pngs = create_QR_codes(
            paper_number, page_number, max_ver + 1, code, Path(td)
        )
        pdf_doc.delete_page()  # this defaults to the last page.

        pdf_doc.new_page(-1)

        pdf_doc[-1].insert_text(
            (120, 50),
            text="This is a page has a qr-code with the wrong version",
            fontsize=18,
            color=[0, 0.75, 0.75],
        )
        # hard-code one qr-code in top-left
        rect = fitz.Rect(50, 50, 50 + 70, 50 + 70)
        pdf_doc[-1].insert_image(rect, pixmap=fitz.Pixmap(qr_pngs[1]), overlay=True)


def append_out_of_range_paper_and_page(pdf_doc):
    """Append two new pages to the pdf - one as test-1 page-999 and one as test-99999 page-1."""
    from plom import SpecVerifier
    from plom.create.mergeAndCodePages import create_QR_codes

    # a rather cludge way to get at the spec via commandline tools
    # really we just need the public code.
    with tempfile.TemporaryDirectory() as td:
        spec_file = Path(td) / "the_spec.toml"
        call_command("plom_preparation_test_spec", "download", f"{spec_file}")
        code = SpecVerifier.from_toml_file(spec_file).spec["publicCode"]

        qr_pngs = create_QR_codes(99999, 1, 1, code, Path(td))
        pdf_doc.new_page(-1)
        pdf_doc[-1].insert_text(
            (120, 200),
            text="This is a page from a non-existent paper",
            fontsize=18,
            color=[0, 0.75, 0.75],
        )
        # hard-code one qr-code in top-left
        rect = fitz.Rect(50, 50, 50 + 70, 50 + 70)
        # the 2nd qr-code goes in NW corner.
        pdf_doc[-1].insert_image(rect, pixmap=fitz.Pixmap(qr_pngs[1]), overlay=True)

        qr_pngs = create_QR_codes(1, 999, 1, code, Path(td))
        pdf_doc.new_page(-1)
        pdf_doc[-1].insert_text(
            (120, 200),
            text="This is a non-existent page from an existing test",
            fontsize=18,
            color=[0, 0.75, 0.75],
        )
        # hard-code one qr-code in top-left
        rect = fitz.Rect(50, 50, 50 + 70, 50 + 70)
        # the 2nd qr-code goes in NW corner.
        pdf_doc[-1].insert_image(rect, pixmap=fitz.Pixmap(qr_pngs[1]), overlay=True)


def _scribble_loop(
    assigned_papers_ids,
    extra_page_path,
    out_file,
    *,
    extra_page_papers=[],
    garbage_page_papers=[],
    duplicate_pages={},
    duplicate_qr=[],
    wrong_version=[],
):
    # extra_page_papers = list of paper_numbers to which we append a couple of extra_pages
    # garbage_page_papers = list of paper_numbers to which we append a garbage page
    # duplicate_pages = dict of n:p = page-p from paper-n = to be duplicated (causing collisions)
    # wrong_version = list of paper_numbers to which we replace last page with a blank but wrong version number.

    # A complete collection of the pdfs created
    with fitz.open() as all_pdf_documents:
        for paper in assigned_papers_ids:
            with fitz.open(paper["path"]) as pdf_document:
                # first put an ID on paper if it is not prenamed.
                if not paper["prenamed"]:
                    scribble_name_and_id(pdf_document, paper["id"], paper["name"])
                paper_number = int(paper["paper_number"])

                if paper_number in wrong_version:
                    make_last_page_with_wrong_version(pdf_document, paper_number)

                if paper_number in extra_page_papers:
                    append_extra_page(
                        pdf_document,
                        paper["paper_number"],
                        paper["id"],
                        extra_page_path,
                    )
                if paper_number in duplicate_pages:
                    append_duplicate_page(pdf_document, duplicate_pages[paper_number])

                # scribble on the pages
                scribble_pages(pdf_document)

                # insert a qr-code from a previous page after scribbling
                if paper_number in duplicate_qr:
                    insert_qr_from_previous_page(pdf_document, paper_number)

                # append a garbage page after the scribbling
                if paper_number in garbage_page_papers:
                    append_garbage_page(pdf_document)

                # finally, append this to the bundle
                all_pdf_documents.insert_pdf(pdf_document)
        # now insert a page from a different assessment to cause a "wrong public code" error
        insert_page_from_another_assessment(all_pdf_documents)
        # append some out-of-range pages
        append_out_of_range_paper_and_page(all_pdf_documents)

        all_pdf_documents.save(out_file)


def scribble_on_exams(
    *,
    number_of_bundles=3,
    extra_page_papers=[],
    garbage_page_papers=[],
    duplicate_pages={},
    duplicate_qr=[],
    wrong_version=[],
):
    classlist = get_classlist_as_dict()
    classlist_length = len(classlist)
    papers_to_print = Path("media/papersToPrint")
    paper_list = [paper for paper in papers_to_print.glob("exam*.pdf")]
    get_extra_page()  # download copy of the extra-page pdf to papersToPrint subdirectory
    extra_page_path = papers_to_print / "extra_page.pdf"

    number_papers_to_use = classlist_length
    papers_to_use = sorted(paper_list)[:number_papers_to_use]

    assigned_papers_ids = assign_students_to_papers(papers_to_use, classlist)
    number_prenamed = sum(1 for X in assigned_papers_ids if X["prenamed"])

    print("v" * 40)
    print(
        f"Making a bundle of {len(papers_to_use)} papers, of which {number_prenamed} are prenamed"
    )
    print(f"Extra pages will be appended to papers: {extra_page_papers}")
    print(f"Garbage pages will be appended after papers: {garbage_page_papers}")
    print(f"Duplicate pages will be inserted: {duplicate_pages}")
    print(
        f"The last page of papers {wrong_version} will be replaced with qr-codes with incorrect versions"
    )
    print(
        f"A qr-code from the second last page of the test-paper paper will be inserted on last page of that paper; in papers: {duplicate_qr}"
    )
    print(
        "A page from a different assessment will be inserted near the end of the bundles"
    )
    print("A page from a non-existent test-paper will be appended to the bundles")
    print("A non-existent page from a test-paper will be appended to the bundles")
    print("^" * 40)

    out_file = Path("fake_bundle.pdf")

    _scribble_loop(
        assigned_papers_ids,
        extra_page_path,
        out_file,
        extra_page_papers=extra_page_papers,
        garbage_page_papers=garbage_page_papers,
        duplicate_pages=duplicate_pages,
        duplicate_qr=duplicate_qr,
        wrong_version=wrong_version,
    )
    # take this single output pdf and split it into given number of bundles, then remove it.
    splitFakeFile(out_file, parts=number_of_bundles)
    out_file.unlink(missing_ok=True)
