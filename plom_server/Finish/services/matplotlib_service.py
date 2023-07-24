# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Julian Lapenna

import base64
from io import BytesIO
from typing import Optional, List

import matplotlib
import matplotlib.cm as cm
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

from Finish.services import GraphingDataService
from Papers.models import Specification


RANGE_BIN_OFFSET = 2


class MatplotlibService:
    """Service for generating matplotlib plots from data."""

    matplotlib.use("Pdf")

    def __init__(self):
        self.gds = GraphingDataService()
        self.spec = Specification.load().spec_dict

        self.student_df = self.gds.get_student_data()
        self.ta_df = self.gds.get_ta_data()

    def check_num_figs(self):
        if len(plt.get_fignums()) > 0:
            print("Warn: ", len(plt.get_fignums()), " figures open.")

    def get_graph_as_base64(self, fig: matplotlib.figure.Figure) -> str:
        """Return the graph as a base64 encoded string.

        Args:
            fig: The figure to encode.

        Returns:
            The base64 encoded string.
        """
        png_bytes = BytesIO()
        fig.savefig(png_bytes, format="png")
        png_bytes.seek(0)
        plt.close()

        return base64.b64encode(png_bytes.read()).decode()

    def histogram_of_total_marks(self, student_df: Optional[pd.DataFrame] = None):
        """Generate a histogram of the total marks.

        Args:
            student_df: Optional dataframe containing the student data. Should be
                a copy or filtered version of self.student_df. If omitted, defaults
                to None and self.student_df is used.

        Returns:
            A matplotlib figure containing the histogram.
        """
        if student_df is None:
            student_df = self.student_df
        assert isinstance(student_df, pd.DataFrame)

        self.check_num_figs()

        fig, ax = plt.subplots()

        ax.hist(
            self.gds.get_total_marks(),
            bins=range(0, self.spec["totalMarks"] + RANGE_BIN_OFFSET),
            ec="black",
            alpha=0.5,
        )
        ax.set_title("Histogram of total marks")
        ax.set_xlabel("Total mark")
        ax.set_ylabel("# of students")

        return fig

    def histogram_of_grades_on_question(
        self, question: int, student_df: Optional[pd.DataFrame] = None
    ):
        """Generate a histogram of the grades on a specific question.

        Args:
            question: The question to generate the histogram for.
            student_df: Optional dataframe containing the student data. Should be
                a copy or filtered version of self.student_df. If omitted, defaults
                to None and self.student_df is used.

        Returns:
            A matplotlib figure containing the histogram.
        """
        if student_df is None:
            student_df = self.student_df
        assert isinstance(student_df, pd.DataFrame)

        self.check_num_figs()

        fig, ax = plt.subplots(figsize=(3.2, 2.4), tight_layout=True)

        bins = range(0, self.spec["question"][str(question)]["mark"] + RANGE_BIN_OFFSET)

        ax.hist(
            student_df["q" + str(question) + "_mark"], bins=bins, ec="black", alpha=0.5
        )
        ax.set_title("Histogram of Q" + str(question) + " marks")
        ax.set_xlabel("Question " + str(question) + " mark")
        ax.set_ylabel("# of students")

        return fig

    def correlation_heatmap_of_questions(self, corr_df: Optional[pd.DataFrame] = None):
        """Generate a correlation heatmap of the questions.

        Args:
            student_df: Optional dataframe containing the student data. Should be
                a copy or filtered version of self.student_df. If omitted, defaults
                to None and self.student_df is used.

        Returns:
            A matplotlib figure containing the correlation heatmap.
        """
        if corr_df is None:
            corr_df = self.gds.get_question_correlation_heatmap_data()
        assert isinstance(corr_df, pd.DataFrame)

        self.check_num_figs()

        plt.figure(figsize=(6.4, 5.12))
        sns.heatmap(corr_df, annot=True, cmap="coolwarm", vmin=-1, vmax=1, square=True)
        plt.title("Correlation between questions")
        plt.xlabel("Question number")
        plt.ylabel("Question number")

        return plt.gcf()

    def histogram_of_grades_on_question_by_ta(
        self, question: int, ta_name: str, ta_df: Optional[pd.DataFrame] = None
    ):
        """Generate a histogram of the grades on a specific question by a specific TA.

        Args:
            question: The question to generate the histogram for.
            ta_name: The name of the TA to generate the histogram for.
            ta_df: Optional dataframe containing the ta data. Should be
                a copy or filtered version of self.ta_df. If omitted, defaults
                to None and self.ta_df is used.

        Returns:
            A matplotlib figure containing the histogram.
        """
        if ta_df is None:
            ta_df = self.gds.get_ta_data_for_ta(
                ta_name, self.gds.get_ta_data_for_question(question_number=question)
            )
        assert isinstance(ta_df, pd.DataFrame)

        self.check_num_figs()

        fig, ax = plt.subplots(figsize=(3.2, 2.4), tight_layout=True)
        bins = range(
            0,
            ta_df["max_score"].max() + RANGE_BIN_OFFSET,
        )

        ax.hist(
            ta_df["score_given"],
            bins=bins,
            ec="black",
            alpha=0.5,
        )
        ax.set_title("Grades for Q" + str(question) + " (by " + ta_name + ")")
        ax.set_xlabel("Mark given")
        ax.set_ylabel("# of times assigned")

        return fig

    def histogram_of_time_spent_marking_each_question(
        self,
        question_number: int,
        marking_times_minutes: List[int],
        max_time: Optional[int] = 0,
        bin_width: Optional[int] = 15,
    ):
        """Generate a histogram of the time spent marking a question.

        Args:
            question_number: The question to generate the histogram for.
            marking_times_minutes: Listlike containing the marking times in minutes.
            max_time: Optional, the maximum time to show on the histogram. If omitted,
                defaults to the maximum time in the marking_times_minutes series.
            bin_width: Optional, the width of each bin on the histogram. If omitted,
                defaults to 15 seconds per bin.

        Returns:
            A matplotlib figure containing the histogram.
        """
        if max_time is 0:
            max_time = max(marking_times_minutes)
        assert max_time > 0

        self.check_num_figs()

        fig, ax = plt.subplots(figsize=(3.2, 2.4), tight_layout=True)
        bins = [t / 60.0 for t in range(0, max_time + bin_width, bin_width)]

        ax.hist(
            marking_times_minutes,
            bins=bins,
            ec="black",
            alpha=0.5,
        )
        ax.set_title("Time spent marking Q" + str(question_number))
        ax.set_xlabel("Time spent (min)")
        ax.set_ylabel("# of papers")

        return fig

    def scatter_time_spent_vs_mark_given(
        self,
        question_number: int,
        times_spent_minutes: List[int],
        marks_given: List[int],
    ):
        """Generate a scatter plot of the time spent marking a question vs the mark given.

        Args:
            question_number: The question to generate the scatter plot for.
            times_spent_minutes: Listlike containing the marking times in minutes.
            marks_given: Listlike containing the marks given.

        Returns:
            A matplotlib figure containing the scatter plot.
        """
        self.check_num_figs()

        fig, ax = plt.subplots(figsize=(3.2, 2.4), tight_layout=True)

        ax.scatter(marks_given, times_spent_minutes, ec="black", alpha=0.5)
        ax.set_title("Q" + str(question_number) + ": Time spent vs Mark given")
        ax.set_ylabel("Time spent (min)")
        ax.set_xlabel("Mark given")

        return fig

    def boxplot_of_marks_given_by_ta(
        self,
        marks: List[List[int]],
        marker_names: List[str],
        question: int,
    ):
        """Generate a boxplot of the marks given by each TA for the specified question.

        The length and order of marks and marker_names should be the same such
        that marks[i] is the list of marks given by marker_names[i].

        Args:
            marks: The dataframe of marks to plot.
            marker_names: The names of the markers.
            question: The question to plot the boxplot for.

        Returns:
            A matplotlib figure containing the boxplot.
        """
        assert len(marks) == len(marker_names)
        self.check_num_figs()

        fig, ax = plt.subplots(figsize=(7.2, 4.0), tight_layout=True)

        # create boxplot and set colours
        for i, mark in reversed(list(enumerate(marks))):
            bp = ax.boxplot(mark, positions=[i], vert=False)
            self.boxplot_set_colors(bp, i / len(marks))
            (hL,) = plt.plot([], c=cm.hsv(i / len(marks)), label=marker_names[i])

        # set legend
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

        plt.xlim(
            [
                0,
                self.gds.get_ta_data_for_question(question_number=int(question))[
                    "max_score"
                ].max(),
            ]
        )

        return fig

    def boxplot_set_colors(self, bp, colour):
        """Set the colours of a boxplot.

        Args:
            bp: The boxplot to set the colours of.
            colour: The colour to set the boxplot to.
        """
        plt.setp(bp["boxes"][0], color=cm.hsv(colour))
        plt.setp(bp["caps"][0], color=cm.hsv(colour))
        plt.setp(bp["caps"][1], color=cm.hsv(colour))
        plt.setp(bp["whiskers"][0], color=cm.hsv(colour))
        plt.setp(bp["whiskers"][1], color=cm.hsv(colour))
        plt.setp(bp["fliers"][0], color=cm.hsv(colour))
        plt.setp(bp["medians"][0], color=cm.hsv(colour))

    def get_report_histogram_of_grades_q(self) -> list:
        """Get a list of histogram graphs of grades by question.

        Made to be used in the report.

        Returns:
            A list of base64-encoded images (str) of the histograms.
        """
        base64_histogram_of_grades_q = []
        marks_for_questions = self.gds.get_marks_for_all_questions(
            student_df=self.student_df
        )
        for question, _ in enumerate(marks_for_questions):
            question += 1  # 1-indexing
            base64_histogram_of_grades_q.append(  # add to the list
                self.get_graph_as_base64(  # each base64-encoded image
                    self.histogram_of_grades_on_question(  # of the histogram
                        question=question
                    )
                )
            )

            self.check_num_figs()

        return base64_histogram_of_grades_q

    def get_report_histogram_of_grades_m(self) -> list:
        """Get a list of lists of histograms of grades by marker by question.

        Made to be used in the report.

        Returns:
            A list of lists of base64-encoded images (str) of the histograms by marker by question.
        """
        base64_histogram_of_grades_m = []
        for marker, scores_for_user in self.gds.get_all_ta_data_by_ta().items():
            questions_marked_by_this_ta = self.gds.get_questions_marked_by_this_ta(
                marker, self.ta_df
            )
            base64_histogram_of_grades_m_q = []

            for question in questions_marked_by_this_ta:
                scores_for_user_for_question = self.gds.get_ta_data_for_question(
                    question_number=question, ta_df=scores_for_user
                )

                base64_histogram_of_grades_m_q.append(
                    self.get_graph_as_base64(
                        self.histogram_of_grades_on_question_by_ta(
                            question=question,
                            ta_name=marker,
                            ta_df=scores_for_user_for_question,
                        )
                    )
                )

            base64_histogram_of_grades_m.append(base64_histogram_of_grades_m_q)

            self.check_num_figs()

        return base64_histogram_of_grades_m

    def get_report_histogram_of_time_spent_marking(self) -> list:
        """Get a list of histograms of time spent marking each question.

        Made to be used in the report.

        Returns:
            A list of base64-encoded images (str) of the histograms.
        """
        max_time = self.gds.get_ta_data()["seconds_spent_marking"].max()
        bin_width = 15  # seconds
        base64_histogram_of_time = []
        for question, marking_times in self.gds.get_times_for_all_questions().items():
            base64_histogram_of_time.append(
                self.get_graph_as_base64(
                    self.histogram_of_time_spent_marking_each_question(
                        question_number=question,
                        marking_times_minutes=marking_times.div(60),
                        max_time=max_time,
                        bin_width=bin_width,
                    )
                )
            )

            self.check_num_figs()

        return base64_histogram_of_time

    def get_report_scatter_of_time_spent_vs_marks_given(self) -> list:
        """Get a list of scatter plots of time spent marking each question vs mark given.

        Made to be used in the report.

        Returns:
            A list of base64-encoded images (str) of the scatter plots.
        """
        base64_scatter_of_time = []
        for question, marking_times in self.gds.get_times_for_all_questions().items():
            times_for_question = marking_times.div(60)
            mark_given_for_question = self.gds.get_scores_for_question(
                question_number=question, ta_df=self.ta_df
            )

            base64_scatter_of_time.append(
                self.get_graph_as_base64(
                    self.scatter_time_spent_vs_mark_given(
                        question_number=question,
                        times_spent_minutes=times_for_question,
                        marks_given=mark_given_for_question,
                    )
                )
            )

            self.check_num_figs()

        return base64_scatter_of_time

    def get_report_boxplot_by_question(self) -> list:
        """Get a list of boxplots of marks given by each marker for each question.

        Made to be used in the report.

        Returns:
            A list of base64-encoded images (str) of the boxplots.
        """
        base_64_boxplots = []
        for (
            question_number,
            question_df,
        ) in self.gds.get_all_ta_data_by_question().items():
            marks_given = []
            # add overall to names
            marker_names = ["Overall"]
            marker_names.extend(
                self.gds.get_tas_that_marked_this_question(question_number, question_df)
            )
            # add the overall marks
            marks_given.append(
                self.gds.get_scores_for_question(
                    question_number=question_number, ta_df=self.ta_df
                )
            )

            for marker_name in marker_names[1:]:
                marks_given.append(
                    self.gds.get_scores_for_ta(ta_name=marker_name, ta_df=question_df),
                )

            base_64_boxplots.append(
                self.get_graph_as_base64(
                    self.boxplot_of_marks_given_by_ta(
                        marks_given, marker_names, question_number
                    )
                )
            )

            self.check_num_figs()

        return base_64_boxplots
