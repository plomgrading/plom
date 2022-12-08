# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2020 Andrew Rechnitzer
# Copyright (C) 2020 Dryden Wiebe
# Copyright (C) 2020 Vala Vakilian
# Copyright (C) 2021-2022 Colin B. Macdonald
# Copyright (C) 2021 Forest Kobayashi

from pathlib import Path
from textwrap import dedent

import fitz

from plom import specdir
from plom.textools import buildLaTeX
from plom.create.mergeAndCodePages import pdf_page_add_stamp, pdf_page_add_name_id_box


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
    *,
    template=specdir / "pageNotSubmitted.pdf",
    outdir=Path("."),
):
    """Builds the substitute empty page for test.

    Arguments:
        test_number (int): Test number.
        page_number (int): Page number.
        version_number (int): Version number

    Keyword Args:
        template (pathlib.Path/str): the template pdf file.
        outdir (pathlib.Path/str): where to save the output.

    Returns:
        libpath.Path: the generated file, in `outdir`, you are responsible
        for deleting it when you're done.
    """
    outdir = Path(outdir)
    pdf = fitz.open(template)
    text = f"Test {test_number:04} [sub] p. {page_number}"
    pdf_page_add_stamp(pdf[0], text)

    image = pdf[0].get_pixmap(alpha=False, matrix=fitz.Matrix(image_scale, image_scale))
    f = outdir / f"pns.{test_number}.{page_number}.{version_number}.png"
    image.save(f)
    pdf.close()
    return f


def build_dnm_page_substitute(
    test_number,
    page_number,
    *,
    template=specdir / "dnmPageNotSubmitted.pdf",
    outdir=Path("."),
):
    """Builds the substitute empty page for test.

    Arguments:
        test_number (int): Test number.
        page_number (int): Page number.

    Keyword Args:
        template (pathlib.Path/str): the template pdf file.
        outdir (pathlib.Path/str): where to save the output.

    Returns:
        libpath.Path: the generated file, in `outdir`, you are responsible
        for deleting it when you're done.
    """
    outdir = Path(outdir)
    pdf = fitz.open(template)
    text = f"Test {test_number:04} DNM[sub] p. {page_number}"
    pdf_page_add_stamp(pdf[0], text)
    image = pdf[0].get_pixmap(alpha=False, matrix=fitz.Matrix(image_scale, image_scale))
    f = outdir / f"dnm.{test_number}.{page_number}.png"
    image.save(f)
    pdf.close()
    return f


def build_homework_question_substitute(
    student_id,
    question_number,
    *,
    template=specdir / "questionNotSubmitted.pdf",
    outdir=Path("."),
):
    """Builds the substitute empty page for homework.

    Arguments:
        student_id (int): Student number ID.
        question_number (int): Question number ID,

    Keyword Args:
        template (pathlib.Path/str): the template pdf file.
        outdir (pathlib.Path/str): where to save the output.

    Returns:
        libpath.Path: the generated file, in `outdir`, you are responsible
        for deleting it when you're done.
    """
    outdir = Path(outdir)
    pdf = fitz.open(template)
    text = f"{student_id} Qidx{question_number}"
    pdf_page_add_stamp(pdf[0], text)
    image = pdf[0].get_pixmap(alpha=False, matrix=fitz.Matrix(image_scale, image_scale))
    f = outdir / f"qns.{student_id}.{question_number}.png"
    image.save(f)
    pdf.close()
    return f


def build_generated_id_page_for_student(
    student_id,
    student_name,
    *,
    template=specdir / "autoGeneratedID.pdf",
    outdir=Path("."),
):
    """Builds an auto-gen ID page

    Arguments:
        student_id (int): Student number ID.
        student_name (str): Student name.

    Keyword Args:
        template (pathlib.Path/str): the template pdf file.
        outdir (pathlib.Path/str): where to save the output.

    Returns:
        libpath.Path: the generated file, in `outdir`, you are responsible
        for deleting it when you're done.
    """
    outdir = Path(outdir)
    pdf = fitz.open(template)
    pdf_page_add_name_id_box(pdf[0], student_name, student_id, signherebox=False)
    image = pdf[0].get_pixmap(alpha=False, matrix=fitz.Matrix(image_scale, image_scale))
    f = outdir / f"autogen.{student_id}.png"
    image.save(f)
    pdf.close()
    return f


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
