# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Julian Lapenna

import datetime as dt

import matplotlib
import matplotlib.cm as cm
import matplotlib.pyplot as plt
import seaborn as sns
from weasyprint import HTML, CSS

from django.core.management.base import BaseCommand

from Finish.services import GraphingDataService
from Finish.services import MatplotlibService
from Mark.models import MarkingTask
from Mark.services import MarkingTaskService
from Papers.models import Specification

RANGE_BIN_OFFSET = 2


class Command(BaseCommand):
    """Generates a PDF report of the marking progress."""

    help = """Generates a PDF report of the marking progress.

    Requires matplotlib, pandas, seaborn, and weasyprint. If calling on demo
    data, run `python manage.py plom_demo --randomarker` first.
    """

    matplotlib.use("Pdf")

    def handle(self, *args, **options):
        print("Building report.")

        gds = GraphingDataService()
        mts = MarkingTaskService()
        mpls = MatplotlibService()
        spec = Specification.load().spec_dict

        student_df = gds.get_student_data()
        ta_df = gds.get_ta_data()

        # info for report
        name = spec["name"]
        longName = spec["longName"]
        totalMarks = spec["totalMarks"]
        date = dt.datetime.now().strftime("%d/%m/%Y %H:%M:%S+00:00")
        num_students = (
            MarkingTask.objects.values_list("paper__paper_number", flat=True)
            .distinct()
            .count()
        )
        average_mark = gds.get_total_average_mark()
        median_mark = gds.get_total_median_mark()
        stdev_mark = gds.get_total_stdev_mark()
        total_tasks = mts.get_n_total_tasks()
        all_marked = mts.get_n_marked_tasks() == total_tasks and total_tasks > 0

        mpls.check_num_figs()

        # histogram of grades
        print("Generating histogram of grades.")
        base64_histogram_of_grades = mpls.get_graph_as_base64(
            mpls.histogram_of_total_marks()
        )

        mpls.check_num_figs()

        # histogram of grades for each question
        print("Generating histograms of grades by question.")
        base64_histogram_of_grades_q = []
        marks_for_questions = gds.get_marks_for_all_questions(student_df=student_df)
        for question, _ in enumerate(marks_for_questions):
            question += 1  # 1-indexing
            base64_histogram_of_grades_q.append(
                mpls.get_graph_as_base64(
                    mpls.histogram_of_grades_on_question(question=question)
                )
            )

            mpls.check_num_figs()

        # correlation heatmap
        print("Generating correlation heatmap.")
        base64_corr = mpls.get_graph_as_base64(
            mpls.correlation_heatmap_of_questions(
                gds.get_question_correlation_heatmap_data()
            )
        )

        mpls.check_num_figs()

        # histogram of grades given by each marker by question
        print("Generating histograms of grades given by marker by question.")
        base64_histogram_of_grades_m = []
        for marker, scores_for_user in gds.get_all_ta_data_by_ta().items():
            questions_marked_by_this_ta = gds.get_questions_marked_by_this_ta(
                marker, ta_df
            )
            base64_histogram_of_grades_m_q = []

            for question in questions_marked_by_this_ta:
                scores_for_user_for_question = gds.get_ta_data_for_question(
                    question_number=question, ta_df=scores_for_user
                )

                base64_histogram_of_grades_m_q.append(
                    mpls.get_graph_as_base64(
                        mpls.histogram_of_grades_on_question_by_ta(
                            question=question,
                            ta_name=marker,
                            ta_df=scores_for_user_for_question,
                        )
                    )
                )

            base64_histogram_of_grades_m.append(base64_histogram_of_grades_m_q)

            mpls.check_num_figs()

        # histogram of time taken to mark each question
        print("Generating histograms of time spent marking each question.")
        max_time = gds.get_ta_data()["seconds_spent_marking"].max()
        bin_width = 15  # seconds
        base64_histogram_of_time = []
        marking_times_for_questions = gds.get_times_for_all_questions()
        for question in marking_times_for_questions:
            fig, ax = plt.subplots(figsize=(3.2, 2.4), tight_layout=True)
            bins = [t / 60.0 for t in range(0, max_time + bin_width, bin_width)]

            ax.hist(
                marking_times_for_questions[question].div(60),
                bins=bins,
                ec="black",
                alpha=0.5,
            )
            ax.set_title("Time spent marking Q" + str(question))
            ax.set_xlabel("Time spent (min)")
            ax.set_ylabel("# of papers")

            base64_histogram_of_time.append(mpls.get_graph_as_base64(fig))

            mpls.check_num_figs()

        # scatter plot of time taken to mark each question vs mark given
        print("Generating scatter plots of time spent marking vs mark given.")
        base64_scatter_of_time = []
        for question in marking_times_for_questions:
            fig, ax = plt.subplots(figsize=(3.2, 2.4), tight_layout=True)

            times_for_question = marking_times_for_questions[question].div(60)
            mark_given_for_question = gds.get_scores_for_question(
                question_number=question, ta_df=ta_df
            )

            ax.scatter(
                mark_given_for_question, times_for_question, ec="black", alpha=0.5
            )
            ax.set_title("Q" + str(question) + ": Time spent vs Mark given")
            ax.set_ylabel("Time spent (min)")
            ax.set_xlabel("Mark given")

            base64_scatter_of_time.append(mpls.get_graph_as_base64(fig))

            mpls.check_num_figs()

        def setBoxColors(bp, colour):
            plt.setp(bp["boxes"][0], color=cm.hsv(colour))
            plt.setp(bp["caps"][0], color=cm.hsv(colour))
            plt.setp(bp["caps"][1], color=cm.hsv(colour))
            plt.setp(bp["whiskers"][0], color=cm.hsv(colour))
            plt.setp(bp["whiskers"][1], color=cm.hsv(colour))
            plt.setp(bp["fliers"][0], color=cm.hsv(colour))
            plt.setp(bp["medians"][0], color=cm.hsv(colour))

        # Box plot of the grades given by each marker for each question
        print("Generating box plots of grades by each marker for each question.")
        base_64_boxplots = []
        for question in spec["question"]:
            fig, ax = plt.subplots(figsize=(7.2, 4.0), tight_layout=True)

            marks = []
            marker_names = ["Overall"]
            marker_names.extend(
                gds.get_tas_that_marked_this_question(int(question), ta_df)
            )
            marks.append(
                gds.get_scores_for_question(question_number=int(question), ta_df=ta_df)
            )
            question_df = gds.get_ta_data_for_question(question_number=int(question))
            for marker in marker_names[1:]:
                marks.append(
                    gds.get_ta_data_for_ta(ta_name=marker, ta_df=question_df)[
                        "score_given"
                    ],
                )
            for i, mark in reversed(list(enumerate(marks))):
                bp = ax.boxplot(mark, positions=[i], vert=False)
                setBoxColors(bp, i / len(marks))
                (hL,) = plt.plot([], c=cm.hsv(i / len(marks)), label=marker_names[i])

            plt.legend(
                loc="center left",
                bbox_to_anchor=(1, 0.5),
                ncol=1,
                fancybox=True,
            )

            ax.set_title("Q" + str(question) + " boxplot by marker")
            ax.set_xlabel("Q" + str(question) + " mark")
            ax.tick_params(
                axis="y",
                which="both",  # both major and minor ticks are affected
                left=False,  # ticks along the bottom edge are off
                right=False,  # ticks along the top edge are off
                labelleft=False,
            )
            # for i, marker in enumerate(markers):
            #     ax.annotate(
            #         marker,
            #         (marks[i], 0),
            #         ha="left",
            #         rotation=60,
            #     )
            plt.xlim(
                [
                    0,
                    gds.get_ta_data_for_question(question_number=int(question))[
                        "max_score"
                    ].max(),
                ]
            )
            # plt.ylim([-0.1, 1])

            base_64_boxplots.append(mpls.get_graph_as_base64(fig))

            mpls.check_num_figs()

        def html_add_title(title: str) -> str:
            """Generate HTML for a title.

            Args:
                title: The title of the section.

            Returns:
                A string of HTML containing the title.
            """
            out = f"""
            <br>
            <p style="break-before: page;"></p>
            <h3>{title}</h3>
            """
            return out

        def html_for_graphs(list_of_graphs: list) -> str:
            """Generate HTML for a list of graphs.

            Args:
                list_of_graphs: A list of base64-encoded graphs.

            Returns:
                A string of HTML containing the graphs.
            """
            out = ""
            for i, graph in enumerate(list_of_graphs):
                odd = i % 2
                if not odd:
                    out += f"""
                    <div class="row">
                    """
                out += f"""
                <div class="col" style="margin-left:0mm;">
                <img src="data:image/png;base64,{graph}" width="50px" height="40px">
                </div>
                """
                if odd:
                    out += f"""
                    </div>
                    """
            if not odd:
                out += f"""
                </div>
                """
            return out

        def html_for_big_graphs(list_of_graphs: list) -> str:
            """Generate HTML for a list of large graphs.

            Args:
                list_of_graphs: A list of base64-encoded graphs.

            Returns:
                A string of HTML containing the graphs.
            """
            out = ""
            for graph in list_of_graphs:
                out += f"""
                <div class="col" style="margin-left:0mm;">
                <img src="data:image/png;base64,{graph}" width="100%" height="100%">
                </div>
                """
            return out

        html = f"""
        <body>
        <h2>Marking report: {longName}</h2>
        """
        if not all_marked:
            html += f"""
            <p style="color:red;">WARNING: Not all papers have been marked.</p>
            """

        html += f"""
        <p>Date: {date}</p>
        <br>
        <h3>Overview</h3>
        <p>Number of students: {num_students}</p>
        <p>Average total mark: {average_mark:.2f}/{totalMarks}</p>
        <p>Median total mark: {median_mark}/{totalMarks}</p>
        <p>Standard deviation of total marks: {stdev_mark:.2f}</p>
        <br>
        <img src="data:image/png;base64,{base64_histogram_of_grades}">
        """

        html += html_add_title("Histogram of total marks")
        html += html_for_graphs(base64_histogram_of_grades_q)

        html += f"""
        <p style="break-before: page;"></p>
        <h3>Correlation heatmap</h3>
        <img src="data:image/png;base64,{base64_corr}">
        """

        html += html_add_title("Histograms of grades by marker by question")

        for index, marker in enumerate(gds.get_all_ta_data_by_ta()):
            html += f"""
            <h4>Grades by {marker}</h4>
            """

            html += html_for_graphs(base64_histogram_of_grades_m[index])

        html += html_add_title(
            "Histograms of time spent marking each question (in minutes)"
        )
        html += html_for_graphs(base64_histogram_of_time)

        html += html_add_title(
            "Scatter plots of time spent marking each question vs mark given"
        )
        html += html_for_graphs(base64_scatter_of_time)

        html += html_add_title(
            "Box plots of grades given by each marker for each question"
        )
        html += html_for_big_graphs(base_64_boxplots)

        def create_pdf(html):
            """Generate a PDF file from a string of HTML."""
            htmldoc = HTML(string=html, base_url="")

            return htmldoc.write_pdf(
                stylesheets=[CSS("./static/css/generate_report.css")]
            )

        def save_pdf_to_disk(pdf_data, file_path):
            """Save the PDF data to a file."""
            with open(file_path, "wb") as f:
                f.write(pdf_data)

        date_filename = ""  # dt.datetime.now().strftime("%Y-%m-%d--%H-%M-%S+00-00")
        filename = "Report-" + name + "--" + date_filename + ".pdf"
        print("Writing to " + filename + ".")

        pdf_data = create_pdf(html)
        save_pdf_to_disk(pdf_data, filename)

        print("Finished saving report.")
