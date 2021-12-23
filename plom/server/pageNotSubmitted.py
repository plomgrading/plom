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

dnm_not_submitted_text = dedent(
    r"""
    \documentclass[12pt,letterpaper]{article}
    \usepackage[]{fullpage}
    \usepackage{tikz}
    \pagestyle{empty}
    \begin{document}
    \emph{This do-not-mark page was not submitted.}
    \vfill
    \begin{tikzpicture}
      \node[rotate=-45, scale=4, red!30] (watermark) at (0,0) {\bfseries
        Not submitted};
    \end{tikzpicture}
    \vfill
    \emph{This do-not-mark page was not submitted.}
    \end{document}
    """
).strip()

id_autogen_text = dedent(
    r"""
    \documentclass[12pt,letterpaper]{article}
    \usepackage[]{fullpage}
    \usepackage{tikz}
    \pagestyle{empty}
    \begin{document}
    \emph{This is an auto-generated ID-page.}
    \vfill
    \begin{tikzpicture}
      \node[rotate=-45, scale=4, black!30] (watermark) at (0,0) {\bfseries
        Generated automatically};
    \end{tikzpicture}
    \vfill
    \emph{This is an auto-generated ID-page.}
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
    image.save(out_dir / f"pns.{test_number}.{page_number}.{version_number}.png")
    pdf.close()

    return True


def build_dnm_page_substitute(
    test_number,
    page_number,
    template=specdir / "dnmPageNotSubmitted.pdf",
    out_dir=Path("."),
):
    """Builds the substitute empty page for test.

    Arguments:
        test_number (int): Test number.
        page_number (int): Page number.
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
    image.save(out_dir / f"dnm.{test_number}.{page_number}.png")
    pdf.close()

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
    image.save(out_dir / f"qns.{student_id}.{question_number}.png")
    pdf.close()

    return True


def build_generated_id_page_for_student(
    student_id,
    student_name,
    template=specdir / "autoGeneratedID.pdf",
    out_dir=Path("."),
):
    """Builds an auto-gen ID page

    Arguments:
        student_id (int): Student number ID.
        student_name (str): Student name.

    Returns:
        bool
    """

    pdf = fitz.open(template)
    y = 42.5  # magic number to center things

    page_width = pdf[0].bound().width
    page_height = pdf[0].bound().height

    txt = "{}\n{}".format(student_id, student_name)

    # make the box a little wider than the required text
    box_width = 1.2 * max(
        fitz.get_text_length(student_id, fontsize=36, fontname="Helvetica"),
        fitz.get_text_length(student_name, fontsize=36, fontname="Helvetica"),
    )
    box1_height = 2 * 36 * 1.5  # two lines of 36 pt and baseline

    name_id_rect = fitz.Rect(
        page_width / 2 - box_width / 2,
        (page_height - box1_height) * y / 100.0,
        page_width / 2 + box_width / 2,
        (page_height - box1_height) * y / 100.0 + box1_height,
    )
    pdf[0].draw_rect(name_id_rect, color=[0, 0, 0], fill=[1, 1, 1], width=2)

    # need this to check name encoding
    def is_possible_to_encode_as(s, encoding):
        try:
            _tmp = s.encode(encoding)
            return True
        except UnicodeEncodeError:
            return False

    if is_possible_to_encode_as(txt, "Latin-1"):
        fontname = "Helvetica"
    elif is_possible_to_encode_as(txt, "gb2312"):
        fontname = "china-ss"
    else:
        raise ValueError("Don't know how to write name {} into PDF".format(txt))

    # We insert the student name and id text box
    excess = pdf[0].insert_textbox(
        name_id_rect,
        txt,
        fontsize=36,
        color=[0, 0, 0],
        fontname=fontname,
        fontfile=None,
        align=1,
    )
    assert excess > 0, "Text didn't fit: student name too long?"

    image = pdf[0].get_pixmap(alpha=False, matrix=fitz.Matrix(image_scale, image_scale))
    image.save(out_dir / f"autogen.{student_id}.png")
    pdf.close()

    return True


def build_autogen_template(template_text, output_file_name):
    """Creates the document from given template text and saves at filename

    Arguments:
        template_text (str): The latex for the template document.
        output_file_name (str): Name of the output file for
            document.

    Returns:
        bool
    """
    with open(output_file_name, "wb") as file:
        return_code, output = buildLaTeX(template_text, file)
    if return_code != 0:
        print(">>> Latex problems - see below <<<\n")
        print(output)
        print(">>> Latex problems - see above <<<")
        return False

    return True


def build_not_submitted_page(output_file_name):
    """Creates the page not submitted document.

    Arguments:
        output_file_name (str): Name of the output file for
            page_not_submitted document.

    Returns:
        bool
    """
    return build_autogen_template(page_not_submitted_text, output_file_name)


def build_not_submitted_question(output_file_name):
    """Creates the page not submitted document.

    Arguments:
        output_file_name (str): Name of the output file for
            question_not_submitted document.

    Returns:
        bool
    """
    return build_autogen_template(question_not_submitted_text, output_file_name)


def build_not_submitted_dnm(output_file_name):
    """Creates the dnm-page not submitted document.

    Arguments:
        output_file_name (str): Name of the output file for
            dnm_not_submitted document.

    Returns:
        bool
    """
    return build_autogen_template(dnm_not_submitted_text, output_file_name)


def build_autogen_id_page(output_file_name):
    """Creates the id-page not submitted document.

    Arguments:
        output_file_name (str): Name of the output file for
            autogen_id_page document

    Returns:
        bool
    """
    return build_autogen_template(id_autogen_text, output_file_name)
