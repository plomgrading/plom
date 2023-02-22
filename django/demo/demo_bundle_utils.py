# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Andrew Rechnitzer

import csv
import fitz
from pathlib import Path
import random
from shlex import split
import subprocess
import tempfile

from plom.create.scribble_utils import (
    scribble_name_and_id,
    scribble_pages,
    splitFakeFile,
)

extra_page_probability = 0.2
extra_page_font_size = 18
garbage_page_probability = 0.2


def get_classlist_as_dict():
    cmd = "python manage.py plom_preparation_classlist download"

    with tempfile.TemporaryDirectory() as td:
        classlist_file = Path(td) / "classlist.csv"
        classlist = []
        subprocess.check_call(split(f"{cmd} {classlist_file}"))
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
    cmd = "python manage.py plom_preparation_extrapage --download papersToPrint/extra_page.pdf"
    subprocess.check_call(split(cmd))


def assign_students_to_papers(paper_list, classlist, *, deterministic=True):
    # prenamed papers are "exam_XXXX_YYYYYYY" and normal are "exam_XXXX"
    all_sid = [row["id"] for row in classlist]
    id_to_name = {X["id"]: X["name"] for X in classlist}

    if not deterministic:  # shuffle the IDs into random order
        random.shuffle(all_sid)
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
    print(f"Append an extra page for test {paper_number} and id {student_id}")
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


def append_garbage_page(pdf_doc):
    print("Appending a garbage page")
    pdf_doc.insert_page(
        -1, text="This is a garbage page", fontsize=18, color=[0, 0.75, 0]
    )


def _scribble_loop(assigned_papers_ids, extra_page_path, out_file, deterministic=True):
    # A complete collection of the pdfs created
    with fitz.open() as all_pdf_documents:
        for paper in assigned_papers_ids:
            with fitz.open(paper["path"]) as pdf_document:
                # first put an ID on paper if it is not prenamed.
                if not paper["prenamed"]:
                    scribble_name_and_id(pdf_document, paper["id"], paper["name"])
                if (not deterministic) and (random.random() < extra_page_probability):
                    append_extra_page(
                        pdf_document,
                        paper["paper_number"],
                        paper["id"],
                        extra_page_path,
                    )
                # scribble on the pages
                scribble_pages(pdf_document)

                # if probability dictates, add a garbage page
                if (not deterministic) and (random.random() < garbage_page_probability):
                    append_garbage_page(pdf_document)

                # finally, append this to the bundle
                all_pdf_documents.insert_pdf(pdf_document)
        all_pdf_documents.save(out_file)


def scribble_on_exams(*, deterministic=True):
    classlist = get_classlist_as_dict()
    classlist_length = len(classlist)
    paper_list = [paper for paper in Path("papersToPrint").glob("exam*.pdf")]
    get_extra_page()  # download copy of the extra-page pdf to papersToPrint subdirectory
    extra_page_path = Path("papersToPrint") / "extra_page.pdf"

    if deterministic:
        number_papers_to_use = classlist_length
        papers_to_use = sorted(paper_list)[:number_papers_to_use]
    else:  # use 90% of the papers generated
        number_papers_to_use = int(classlist_length * 0.9)
        papers_to_use = sorted(random.sample(paper_list, k=number_papers_to_use))

    assigned_papers_ids = assign_students_to_papers(
        papers_to_use, classlist, deterministic=deterministic
    )
    number_prenamed = sum(1 for X in assigned_papers_ids if X["prenamed"])

    print("v" * 40)
    print(
        f"Making a bundle of {len(papers_to_use)} papers, of which {number_prenamed} are prenamed"
    )
    if deterministic:
        print("The bundle is being built deterministically")
    else:
        print("The bundle is being built with some randomness")
    print("^" * 40)

    out_file = Path("fake_bundle.pdf")

    _scribble_loop(
        assigned_papers_ids, extra_page_path, out_file, deterministic=deterministic
    )
    # take this single output pdf and split it into three, then remove it.
    splitFakeFile(out_file)
    out_file.unlink(missing_ok=True)
