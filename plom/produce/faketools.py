# Copyright (C) 2019-2020 Colin B. Macdonald
# Copyright (C) 2020 Andrew Rechnitzer
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Plom tools for scribbling fake answers on PDF files"""

__copyright__ = "Copyright (C) 2019-2020 Andrew Rechnitzer and Colin B. Macdonald"
__credits__ = "The Plom Project Developers"
__license__ = "AGPL-3.0-or-later"

import os
import random
from pathlib import Path
from glob import glob
import argparse
import csv
import random
import json
import base64
from getpass import getpass

import pkg_resources
import fitz

from . import paperdir as _paperdir
from plom import __version__
from plom.messenger import ManagerMessenger
from plom.plom_exceptions import PlomExistingLoginException


# load the digit images
digits_folder_path = "produce/digits.json"
digit_array = json.load(pkg_resources.resource_stream("plom", digits_folder_path))
# how many of each digit were collected

number_of_digits = len(digit_array) // 10
assert len(digit_array) % 10 == 0


possible_answers = [
    "I am so sorry, I really did study this... :(",
    "I know this, I just can't explain it",
    "Hey, at least its not in Comic Sans",
    "Life moves pretty fast. If you don't stop and look around once in a while, "
    "you could miss it.  -- Ferris Bueler",
    "Stupid is as stupid does.  -- Forrest Gump",
    "Of course, it is very important to be sober when you take an exam.  "
    "Many worthwhile careers in the street-cleansing, fruit-picking and "
    "subway-guitar-playing industries have been founded on a lack of "
    "understanding of this simple fact.  -- Terry Pratchett",
    "The fundamental cause of the trouble in the modern world today is that "
    "the stupid are cocksure while the intelligent are full of doubt.  "
    "-- Bertrand Russell",
    "Numbers is hardly real and they never have feelings\n"
    "But you push too hard, even numbers got limits.  -- Mos Def",
    "I was doin' 150 miles an hour sideways\n"
    "And 500 feet down at the same time\n"
    "I was lookin' for the cops, 'cuz you know\n"
    "I knew that it, it was illegal  -- Arlo Guthrie",
    "But there will always be science, engineering, and technology.  "
    "And there will always, always be mathematics.  -- Katherine Johnson",
    "Is 5 = 1?  Let's see... multiply both sides by 0.  "
    "Now 0 = 0 so therefore 5 = 1.",
    "I mean, you could claim that anything's real if the only basis for "
    "believing in it is that nobody's proved it doesn't exist!  -- Hermione Granger",
]


def fill_in_fake_data_on_exams(paper_dir_path, classlist, outfile, which=None):
    """Fill-in exams with fake data for demo or testing.

    Arguments:
        paper_dir_path {Str or convertable to pathlib obj} -- Directory containing the blank exams.
        classlist (list): ordered list of (sid, sname) pairs.
        outfile {Str} -- Path to write results into this concatenated PDF file.

    Keyword Arguments:
        which {type} -- by default, scribble on all exams or specify
                           something like `which=range(10, 16)` here to scribble on a
                           subset. (default: {None})
    """

    # Customizable data
    blue = [0, 0, 0.75]
    student_number_length = 8
    extra_page_probability = 0.2
    digit_font_size = 24
    answer_font_size = 13
    extra_page_font_size = 18

    # We create the path objects
    paper_dir_path = Path(paper_dir_path)
    out_file_path = Path(outfile)

    print("Annotating papers with fake student data and scribbling on pages...")
    if not which:
        named_papers_paths = glob(
            str(paper_dir_path / "exam_*_*.pdf")
        )  # those with an ID number
        papers_paths = sorted(glob(str(paper_dir_path / "exam_*.pdf")))  # everything
    else:
        papers_paths = sorted(
            [
                paper_dir_path / "exam_{}.pdf".format(str(index).zfill(4))
                for index in which
            ]
        )

    used_id_list = []
    # need to avoid any student numbers already used to name papers - look at file names
    for index, file_name in enumerate(named_papers_paths):
        used_id_list.append(os.path.split(file_name)[1].split(".")[0].split("_")[-1])
    # now load in the student names and numbers -only those not used to prename
    clean_id_dict = {}  # not used
    for sid, sname in classlist:
        if sid not in used_id_list:
            clean_id_dict[sid] = sname

    # now grab a random selection of IDs from the dict.
    # we need len(papers_paths) - len(named_papers_paths) of them
    id_sample = random.sample(
        list(clean_id_dict.keys()), len(papers_paths) - len(named_papers_paths)
    )

    # A complete collection of the pdfs created
    all_pdf_documents = fitz.open()

    clean_count = 0
    for index, file_name in enumerate(papers_paths):
        if file_name in named_papers_paths:
            print("{} - prenamed paper - scribbled".format(os.path.basename(file_name)))
        else:
            student_number = id_sample[clean_count]
            student_name = clean_id_dict[student_number]
            clean_count += 1
            print(
                "{} - scribbled using {} {}".format(
                    os.path.basename(file_name), student_number, student_name
                )
            )

        pdf_document = fitz.open(file_name)
        front_page = pdf_document[0]

        # First we input the student names
        if file_name not in named_papers_paths:  # can draw on front page
            # insert digit images into rectangles - some hackery required to get correct positions.
            width = 28
            border = 8
            for digit_index in range(student_number_length):
                rect1 = fitz.Rect(
                    220 + border * digit_index + width * digit_index,
                    265,
                    220 + border * digit_index + width * (digit_index + 1),
                    265 + width,
                )
                uuImg = digit_array[
                    int(student_number[digit_index]) * number_of_digits
                    + random.randrange(number_of_digits)
                ]  # uu-encoded png
                img_BString = base64.b64decode(uuImg)
                front_page.insertImage(rect1, stream=img_BString, keep_proportion=True)
                # TODO - there should be an assert or something here?

            digit_rectangle = fitz.Rect(228, 335, 550, 450)
            insertion_confirmed = front_page.insertTextbox(
                digit_rectangle,
                student_name,
                fontsize=digit_font_size,
                color=blue,
                fontname="Helvetica",
                fontfile=None,
                align=0,
            )
            assert insertion_confirmed > 0

        # Write some random answers on the pages
        for page_index, pdf_page in enumerate(pdf_document):
            random_answer_rect = fitz.Rect(
                100 + 30 * random.random(), 150 + 20 * random.random(), 500, 500
            )
            random_answer_text = random.choice(possible_answers)

            # TODO: "helv" vs "Helvetica"
            if page_index >= 1:
                insertion_confirmed = pdf_page.insertTextbox(
                    random_answer_rect,
                    random_answer_text,
                    fontsize=answer_font_size,
                    color=blue,
                    fontname="helv",
                    fontfile=None,
                    align=0,
                )
                assert insertion_confirmed > 0

        # delete last page from the zeroth test.
        if index == 0:
            pdf_document.deletePage(-1)
            print("Deleting last page of test {}".format(file_name))

        # We then add the pdfs into the document collection
        all_pdf_documents.insertPDF(pdf_document)

        # For a comprehensive test, we will add some extrapages with the probability of 0.2 precent
        if random.random() < extra_page_probability:
            # folder_name/exam_XXXX.pdf or folder_name/exam_XXXX_YYYYYYY.pdf,
            # file_pdf_name drops the folder name and the .pdf parts
            file_pdf_name = os.path.splitext(os.path.basename(file_name))[0]

            # Then we get the test number and student_number from file_pdf_name
            test_number = file_pdf_name.split("_")[1]
            if (
                file_name in named_papers_paths
            ):  # file_pdf_name is exam_XXXX_YYYYYYY.pdf
                student_number = file_pdf_name.split("_")[2]

            print(
                "  making an extra page for test {} and sid {}".format(
                    test_number, student_number
                )
            )
            all_pdf_documents.insertPage(
                -1,
                text="EXTRA PAGE - t{} Q1 - {}".format(test_number, student_number),
                fontsize=extra_page_font_size,
                color=blue,
            )

        pdf_document.close()

    # need to use `str(out_file_path)` for pumypdf < 1.16.14
    # https://github.com/pymupdf/PyMuPDF/issues/466
    # Here we only need to save the generated pdf files with random test answers
    all_pdf_documents.save(out_file_path)
    print('Assembled in "{}"'.format(out_file_path))


def make_garbage_page(out_file_path, number_of_grarbage_pages=1):
    """Randomly genertes garbage pages.

    Purely used for testing.

    Arguments:
        out_file_path {Str} -- String path for a pdf file to which we will add a random garbage page

    Keyword Arguments:
        number_of_grarbage_pages {int} -- Number of added garbage pages for this document (default: {1})
    """

    # Customizable data
    green = [0, 0.75, 0]
    garbage_page_font_size = 18

    all_pdf_documents = fitz.open(out_file_path)
    print("Doc has {} pages".format(len(all_pdf_documents)))
    for index in range(number_of_grarbage_pages):
        garbage_page_index = random.randint(-1, len(all_pdf_documents))
        print("Insert garbage page at garbage_page_index={}".format(garbage_page_index))
        all_pdf_documents.insertPage(
            garbage_page_index, text="This is a garbage page", fontsize=18, color=green
        )
    all_pdf_documents.saveIncr()


def download_classlist(server=None, password=None):
    """Download list of student IDs/names from server."""
    if server and ":" in server:
        s, p = server.split(":")
        msgr = ManagerMessenger(s, port=p)
    else:
        msgr = ManagerMessenger(server)
    msgr.start()

    if not password:
        password = getpass('Please enter the "manager" password: ')

    try:
        msgr.requestAndSaveToken("manager", password)
    except PlomExistingLoginException:
        print(
            "You appear to be already logged in!\n\n"
            "  * Perhaps a previous session crashed?\n"
            "  * Do you have another management tool running,\n"
            "    e.g., on another computer?\n\n"
            'In order to force-logout the existing authorisation run "plom-build clear"'
        )
        exit(10)
    try:
        classlist = msgr.IDrequestClasslist()
    except PlomBenignException as e:
        print("Failed to download classlist: {}".format(e))
        exit(4)
    finally:
        msgr.closeUser()
        msgr.stop()
    return classlist


def main():
    """Main function used for running.

    1. Generates teh files.
    2. Creates the fake data filled pdfs using fill_in_fake_data_on_exams.
    3. Deletes from the pdf file using delete_one_page.
    4. We also add some garbage pages using delete_one_page.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--version", action="version", version="%(prog)s " + __version__
    )
    parser.add_argument("-s", "--server", metavar="SERVER[:PORT]", action="store")
    parser.add_argument("-w", "--password", type=str, help='for the "manager" user')
    args = parser.parse_args()

    out_file_path = "fake_scribbled_exams.pdf"
    classlist = download_classlist(args.server, args.password)

    fill_in_fake_data_on_exams(_paperdir, classlist, out_file_path)
    make_garbage_page(out_file_path, number_of_grarbage_pages=2)


if __name__ == "__main__":
    main()
