# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Julian Lapenna

import base64
from io import BytesIO
from typing import Optional

import matplotlib
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
        """Generate a histogram of the grades on a specific question.

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
