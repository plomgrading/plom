# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2020 Andrew Rechnitzer
# Copyright (C) 2020 Dryden Wiebe
# Copyright (C) 2020 Vala Vakilian
# Copyright (C) 2021 Colin B. Macdonald

import fitz

from plom import specdir
from plom.textools import buildLaTeX


question_not_submitted_text = r"""
    \documentclass[12pt,letterpaper]{article}
    \usepackage[]{fullpage}
    \usepackage{xcolor}
    \usepackage[printwatermark]{xwatermark}
    \newwatermark[allpages,color=red!30,angle=-45,scale=2]{Question not submitted}
    \pagestyle{empty}
    \begin{document}
    \emph{This question was not submitted.}
    \vfill
    \emph{This question was not submitted.}
    \end{document}
    """

page_not_submitted_text = r"""
    \documentclass[12pt,letterpaper]{article}
    \usepackage[]{fullpage}
    \usepackage{xcolor}
    \usepackage[printwatermark]{xwatermark}
    \newwatermark[allpages,color=red!30,angle=-45,scale=2]{Page not submitted}
    \pagestyle{empty}
    \begin{document}
    \emph{This page of the test was not submitted.}
    \vfill
    \emph{This page of the test was not submitted.}
    \end{document}
    """


image_scale = 200 / 72


def build_test_page_substitute(test_number, page_number, version_number):
    """Builds the substitute empty page for test.

    Arguments:
        test_number (int): Test number.
        page_number (int): Page number.
        version_number (int): Version number

    Returns:
        bool
    """
    page_not_submitted_pdf = fitz.open(specdir / "pageNotSubmitted.pdf")

    # create a box for the test number near top-centre
    # Get page width and use it to inset this text into the page
    page_width = page_not_submitted_pdf[0].bound().width
    rect = fitz.Rect(page_width // 2 - 40, 20, page_width // 2 + 40, 44)
    text = "{}.{}".format(str(test_number).zfill(4), str(page_number).zfill(2))
    insertion_confirmed = page_not_submitted_pdf[0].insert_textbox(
        rect,
        text,
        fontsize=18,
        color=[0, 0, 0],
        fontname="Helvetica",
        fontfile=None,
        align=1,
    )
    assert (
        insertion_confirmed > 0
    ), "Text didn't fit: shortname too long?  or font issue/bug?"

    page_not_submitted_pdf[0].draw_rect(rect, color=[0, 0, 0])

    page_not_submitted_image = page_not_submitted_pdf[0].get_pixmap(
        alpha=False, matrix=fitz.Matrix(image_scale, image_scale)
    )
    page_not_submitted_image.writePNG(
        "pns.{}.{}.{}.png".format(test_number, page_number, version_number)
    )

    return True


def build_homework_question_substitute(student_id, question_number):
    """Builds the substitute empty page for homeork.

    Arguments:
        student_id (int): Student number ID.
        question_number (int): Question number ID,

    Returns:
        bool
    """
    question_not_submitted_pdf = fitz.open(specdir / "questionNotSubmitted.pdf")

    # create a box for the test number near top-centre
    # Get page width and use it to inset this text into the page
    page_width = question_not_submitted_pdf[0].bound().width
    rect = fitz.Rect(page_width // 2 - 50, 20, page_width // 2 + 50, 54)
    text = "{}.{}".format(student_id, question_number)
    insertion_confirmed = question_not_submitted_pdf[0].insert_textbox(
        rect,
        text,
        fontsize=18,
        color=[0, 0, 0],
        fontname="Helvetica",
        fontfile=None,
        align=1,
    )
    assert (
        insertion_confirmed > 0
    ), "Text didn't fit: shortname too long?  or font issue/bug?"

    question_not_submitted_pdf[0].draw_rect(rect, color=[0, 0, 0])

    question_not_submitted_image = question_not_submitted_pdf[0].get_pixmap(
        alpha=False, matrix=fitz.Matrix(image_scale, image_scale)
    )
    question_not_submitted_image.writePNG(
        "qns.{}.{}.png".format(student_id, question_number)
    )

    return True


def build_not_submitted_page(output_file_name):
    """Creates the page not submitted document.

    Arguments:
        output_file_name (str): Name of the output file for
            page_not_submitted document.

    Returns:
        bool
    """
    with open(output_file_name, "wb") as file:
        return_code, output = buildLaTeX(page_not_submitted_text, file)
    if return_code != 0:
        print(">>> Latex problems - see below <<<\n")
        print(output)
        print(">>> Latex problems - see above <<<")
        return False

    return True


def build_not_submitted_question(output_file_name):
    """Creates the page not submitted document.

    Arguments:
        output_file_name (str): Name of the output file for
            question_not_submitted document.

    Returns:
        bool
    """
    with open(output_file_name, "wb") as file:
        return_code, output = buildLaTeX(question_not_submitted_text, file)
    if return_code != 0:
        print(">>> Latex problems - see below <<<\n")
        print(output)
        print(">>> Latex problems - see above <<<")
        return False

    return True
