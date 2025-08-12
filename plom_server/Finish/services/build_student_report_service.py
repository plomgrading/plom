# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Bryan Tanady
# Copyright (C) 2024-2025 Colin B. Macdonald
# Copyright (C) 2024-2025 Andrew Rechnitzer
# Copyright (C) 2025 Philip D. Loewen

from datetime import datetime
from pathlib import Path
from statistics import mean, median, mode, stdev, quantiles
from typing import Any

from django.conf import settings

from plom_server.Papers.services import SpecificationService
from ..services import StudentMarkService
from plom_server.QuestionTags.services import QuestionTagService


def _get_descriptive_statistics_from_score_list(
    scores: list[float],
) -> dict[str, float]:
    """Return descriptive statistics from a list of scores.

    Gives dict of count, max, min, median, mean, mode, stddev, percentile25, percentile75.
    """
    if len(scores) > 1:
        quants = quantiles(scores)
        standard_deviation = stdev(scores)
    else:
        # Functions quantiles() and stdev() don't work in the
        # degenerate case of just one score. Define appropriate
        # results directly.
        quants = [scores[0], scores[0], scores[0]]
        standard_deviation = 0.0

    return {
        "count": len(scores),
        "max": max(scores),
        "min": min(scores),
        "median": median(scores),
        "mean": mean(scores),
        "mode": mode(scores),
        "stddev": standard_deviation,
        "percentile25": quants[0],
        "percentile75": quants[2],
    }


def brief_report_pdf_builder(
    paper_number,
    total_score_list: list[float],
    question_score_lists: dict[int, list[float]],
) -> dict[str, Any]:
    """Build a Student Report PDF file report and return it as bytes.

    Args:
        paper_number: the number of the paper
        total_score_list: a list of total scores of all completely
            marked papers.
        question_score_lists: a dict (keyed by question index) of lists
            of scores of all marked questions.

    Returns:
        A dictionary with the bytes of a PDF file, a suggested
        filename, and the export timestamp.

    Raises:
        ValueError: lots of cases with NaN, usually indicating marking
            is incomplete, because the pandas library uses NaN for
            missing data.

    This method uses a slightly strange mix of Django internals to use
    the Django-templating system.  The rendered html (string) is then
    fed to WEasyPrint to make a PDF.
    """
    from django.template.loader import get_template
    from weasyprint import HTML, CSS
    from . import MinimalPlotService

    paper_info = StudentMarkService.get_paper_id_and_marks(paper_number)
    timestamp = datetime.utcnow()
    timestamp_str = timestamp.strftime("%d/%m/%Y at %H:%M (UTC)")

    context = {
        "longname": SpecificationService.get_longname(),
        "timestamp_str": timestamp_str,
        "totalMarks": SpecificationService.get_total_marks(),
        "name": paper_info["name"],
        "sid": paper_info["sid"],
        "grade": paper_info["total"],
        "total_stats": _get_descriptive_statistics_from_score_list(total_score_list),
        "kde_graph": MinimalPlotService.kde_plot_of_total_marks(
            total_score_list, highlighted_score=paper_info["total"]
        ),
        "boxplots": [
            MinimalPlotService().boxplot_of_grades_on_question(
                qi, score_list, highlighted_score=paper_info[qi]
            )
            for qi, score_list in question_score_lists.items()
        ],
        "pedagogy_tags": None,
        "pedagogy_tags_graph": None,
    }
    # don't generate the lollipop graph if there are no pedagogy tags
    tag_to_questions = QuestionTagService.get_tag_to_question_links()
    if tag_to_questions:
        qidx_to_html = SpecificationService.get_question_labels_str_and_html_map()
        tag_descriptions = QuestionTagService.get_pedagogy_tag_descriptions()
        context["pedagogy_tags"] = {
            ptag: (
                # translate the qidx to html label
                [qidx_to_html[qi][1] for qi in sorted(qidx_list)],
                tag_descriptions[ptag],
            )
            for ptag, qidx_list in tag_to_questions.items()
        }
        context["pedagogy_tags_graph"] = MinimalPlotService().lollipop_of_pedagogy_tags(
            tag_to_questions,
            {qi: paper_info[qi] for qi in question_score_lists},
            paper_info["question_max_marks"],
        )

    # TODO: suspicious if this will always work, out-of-tree
    report_template = get_template("Finish/Reports/brief_student_report.html")
    # print(f"DEBUG: the report template is: {report_template}")
    rendered_html = report_template.render(context)

    # We want this, but done "properly":
    # # css = CSS("./static/css/generate_report.css")
    # see also ReportPDFService.py

    # TODO: is this really static access?  this CSS is not used by the outside world
    # # from django.templatetags.static import static
    # # static("css/generate_report.css")
    # produces `s/tatic/css/generate_report.css`, like part of a URL

    # TODO: would this need static.css to be a python module?
    # from importlib import resources
    # css_filelike = resources.files("plom_server.static.css") / "generate_report.css"

    # TODO: for now, just grab the file with direct access (which might not work if
    # we're installed inside a .zip file or something esoteric like that).
    import plom_server

    path = Path(plom_server.__path__[0]) / "static/css/generate_report.css"
    # print(f"DEBUG: getting CSS directly from {path}")
    css = CSS(path)

    pdf_data = HTML(string=rendered_html, base_url="").write_pdf(stylesheets=[css])
    shortname = SpecificationService.get_shortname()
    sid = paper_info["sid"]
    filename = f"{shortname}_report_{sid}.pdf"
    return {
        "bytes": pdf_data,
        "filename": filename,
        "timestamp": timestamp,
    }


class BuildStudentReportService:
    """Class that contains helper functions for building student report pdf."""

    def build_brief_report(
        self,
        paper_number: int,
        total_score_list: list[float],
        question_score_lists: dict[int, list[float]],
    ) -> dict[str, Any]:
        """Build brief student report for the given paper number.

        Note - in future will use this to replace the 'build_one_report'
        function.

        Args:
            paper_number: the paper_number to be built a report.
            total_score_list: list of scores of all marked assessments.
            question_score_lists: dict, keyed by question index, of
                lists of scores for each question.

        Returns:
            A dictionary with student report PDF file in bytes.
        """
        # TODO: why we making this ourselves?  Should be a model problem
        outdir = settings.MEDIA_ROOT / "student_report"
        outdir.mkdir(exist_ok=True)

        return brief_report_pdf_builder(
            paper_number, total_score_list, question_score_lists
        )
