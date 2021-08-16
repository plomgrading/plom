# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2020 Andrew Rechnitzer
# Copyright (C) 2020 Dryden Wiebe
# Copyright (C) 2020 Vala Vakilian
# Copyright (C) 2021 Colin B. Macdonald
# Copyright (C) 2021 Forest Kobayashi

from pathlib import Path
from textwrap import dedent

import fitz

from plom import specdir
from plom.textools import buildLaTeX


# TODO: letterpaper hardcoded
question_not_submitted_text = dedent(
    r"""
    \documentclass[12pt,letterpaper]{article}
    \usepackage[]{fullpage}
    \usepackage{tikz}
    \pagestyle{empty}
    \begin{document}
    \emph{This question was not submitted.}
    \vfill
    \begin{tikzpicture}
      \node[rotate=-45, scale=4, red!30] (watermark) at (0,0) {\bfseries
        Question not submitted};
    \end{tikzpicture}
    \vfill
    \emph{This question was not submitted.}
    \end{document}
    """
).strip()

page_not_submitted_text = dedent(
    r"""
    \documentclass[12pt,letterpaper]{article}
    \usepackage[]{fullpage}
    \usepackage{tikz}
    \pagestyle{empty}
    \begin{document}
    \emph{This page of the test was not submitted.}
    \vfill
    \begin{tikzpicture}
      \node[rotate=-45, scale=4, red!30] (watermark) at (0,0) {\bfseries
        Page not submitted};
    \end{tikzpicture}
    \vfill
    \emph{This page of the test was not submitted.}
    \end{document}
    """
).strip()


image_scale = 200 / 72


def build_test_page_substitute(
    test_number,
    page_number,
    version_number,
    template=specdir / "pageNotSubmitted.pdf",
    out_dir=Path("."),
):
    """Builds the substitute empty page for test.

    Arguments:
        test_number (int): Test number.
        page_number (int): Page number.
        version_number (int): Version number
        template (pathlib.Path/str): the template pdf file.
        out_dir (pathlib.Path/str): where to save the output.

    Returns:
        bool
    """
    pdf = fitz.open(template)

    # create a box for the test number near top-centre
    # Get page width and use it to inset this text into the page
    page_width = pdf[0].bound().width
    rect = fitz.Rect(page_width // 2 - 40, 20, page_width // 2 + 40, 44)
    text = "{}.{}".format(str(test_number).zfill(4), str(page_number).zfill(2))
    excess = pdf[0].insert_textbox(
        rect,
        text,
        fontsize=18,
        color=[0, 0, 0],
        fontname="Helvetica",
        fontfile=None,
        align=1,
    )
    assert excess > 0, "Text didn't fit: paper label too long?"

    pdf[0].draw_rect(rect, color=[0, 0, 0])

    image = pdf[0].get_pixmap(alpha=False, matrix=fitz.Matrix(image_scale, image_scale))
    image.writePNG(
        str(
            out_dir
            / "pns.{}.{}.{}.png".format(test_number, page_number, version_number)
        )
    )

    return True


def build_homework_question_substitute(
    student_id,
    question_number,
    template=specdir / "questionNotSubmitted.pdf",
    out_dir=Path("."),
):
    """Builds the substitute empty page for homework.

    Arguments:
        student_id (int): Student number ID.
        question_number (int): Question number ID,

    Returns:
        bool
    """
    pdf = fitz.open(template)

    # create a box for the test number near top-centre
    # Get page width and use it to inset this text into the page
    page_width = pdf[0].bound().width
    rect = fitz.Rect(page_width // 2 - 50, 20, page_width // 2 + 50, 54)
    text = "{}.{}".format(student_id, question_number)
    excess = pdf[0].insert_textbox(
        rect,
        text,
        fontsize=18,
        color=[0, 0, 0],
        fontname="Helvetica",
        fontfile=None,
        align=1,
    )
    assert excess > 0, "Text didn't fit: paper label too long?"

    pdf[0].draw_rect(rect, color=[0, 0, 0])

    image = pdf[0].get_pixmap(alpha=False, matrix=fitz.Matrix(image_scale, image_scale))
    image.writePNG(str(out_dir / "qns.{}.{}.png".format(student_id, question_number)))

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
