# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Julian Lapenna

import base64
from io import BytesIO
from typing import List, Optional, Union, Any

import matplotlib
import matplotlib.cm as cm
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from . import DataExtractionService
from Papers.services import SpecificationService


RANGE_BIN_OFFSET = 2


class MatplotlibService:
    """Service for generating matplotlib plots from data."""

    matplotlib.use("Agg")

    def __init__(self):
        self.des = DataExtractionService()
        self.spec = SpecificationService.get_the_spec()

        self.student_df = self.des._get_student_data()
        self.ta_df = self.des._get_ta_data()
        self.formats = ["base64", "bytes"]

    def ensure_all_figures_closed(self):
        """Ensure that all matplotlib figures are closed.

        Raises:
            AssertionError: If not all figures are closed.
        """
        assert plt.get_fignums() == [], "Not all matplotlib figures were closed."

    def get_graph_as_BytesIO(self, fig: matplotlib.figure.Figure) -> BytesIO:
        """Return the graph as a BytesIO.

        Args:
            fig: The figure to save.

        Returns:
            The BytesIO object.
        """
        png_bytes = BytesIO()
        fig.savefig(png_bytes, format="png")
        png_bytes.seek(0)
        plt.close()

        return png_bytes

    def get_graph_as_base64(self, bytes: BytesIO) -> str:
        """Return the graph as a base64 encoded string.

        Args:
            bytes: The bytes to encode.

        Returns:
            The base64 encoded string.
        """
        return base64.b64encode(bytes.read()).decode()

    def histogram_of_total_marks(
        self, *, format: str = "base64"
    ) -> Union[BytesIO, str]:
        """Generate a histogram of the total marks.

        Keyword Args:
            format: The format to return the graph in. Should be either "base64"
                or "bytes". If omitted, defaults to "base64".

        Returns:
            Base64 encoded string or bytes containing the histogram.
        """
        assert format in self.formats
        self.ensure_all_figures_closed()

        fig, ax = plt.subplots()

        ax.hist(
            self.des.get_total_marks(),
            bins=np.arange(self.spec["totalMarks"] + RANGE_BIN_OFFSET) - 0.5,
            ec="black",
            alpha=0.5,
            width=0.8,
            align="mid",
        )
        ax.set_title("Histogram of total marks")
        ax.set_xlabel("Total mark")
        ax.set_ylabel("# of students")
        plt.grid(True, alpha=0.5)

        graph_bytes = self.get_graph_as_BytesIO(fig)
        self.ensure_all_figures_closed()

        if format == "bytes":
            return graph_bytes
        else:
            return self.get_graph_as_base64(graph_bytes)

    def histogram_of_grades_on_question_version(
        self,
        question: int,
        *,
        versions: bool = False,
        student_df: Optional[pd.DataFrame] = None,
        format: str = "base64",
    ) -> Union[BytesIO, str]:
        """Generate a histogram of the grades on a specific question.

        Args:
            question: The question number.

        Keyword Args:
            versions: Whether to split the histogram into versions. If omitted,
                defaults to False.
            student_df: Optional dataframe containing the student data. Should be
                a copy or filtered version of self.student_df. If omitted, defaults
                to None and self.student_df is used.
            format: The format to return the graph in. Should be either "base64"
                or "bytes". If omitted, defaults to "base64".

        Returns:
            Base64 encoded string or bytes containing the histogram.
        """
        if student_df is None:
            student_df = self.student_df

        assert isinstance(student_df, pd.DataFrame)
        assert format in self.formats
        self.ensure_all_figures_closed()

        plot_series = []
        if versions is True:
            for version in range(
                1, round(student_df["q" + str(question) + "_version"].max()) + 1
            ):
                plot_series.append(
                    student_df[
                        (student_df["q" + str(question) + "_version"] == version)
                    ]["q" + str(question) + "_mark"]
                )
            labels = ["Version " + str(i) for i in range(1, len(plot_series) + 1)]
        else:
            plot_series.append(student_df["q" + str(question) + "_mark"])

        fig, ax = plt.subplots(figsize=(6.8, 4.2), tight_layout=True)

        bins = (
            np.arange(self.spec["question"][str(question)]["mark"] + RANGE_BIN_OFFSET)
            - 0.5
        )

        ax.hist(plot_series, bins=bins, ec="black", alpha=0.5)
        ax.set_title("Histogram of Q" + str(question) + " marks")
        ax.set_xlabel("Question " + str(question) + " mark")
        ax.set_ylabel("# of students")
        if versions is True:
            ax.legend(
                labels,
                loc="center left",
                bbox_to_anchor=(1, 0.5),
                ncol=1,
                fancybox=True,
            )
        plt.grid(True, alpha=0.5)

        graph_bytes = self.get_graph_as_BytesIO(fig)
        self.ensure_all_figures_closed()

        if format == "bytes":
            return graph_bytes
        else:
            return self.get_graph_as_base64(graph_bytes)

    def correlation_heatmap_of_questions(
        self, *, corr_df: Optional[pd.DataFrame] = None, format: str = "base64"
    ) -> Union[BytesIO, str]:
        """Generate a correlation heatmap of the questions.

        Keyword Args:
            corr_df: Optional dataframe containing the student data. Should be
                a copy or filtered version of self.student_df. If omitted, defaults
                to None and self.student_df is used.
            format: The format to return the graph in. Should be either "base64"
                or "bytes". If omitted, defaults to "base64".

        Returns:
            Base64 encoded string or bytes containing the correlation heatmap.
        """
        if corr_df is None:
            corr_df = self.des._get_question_correlation_heatmap_data()

        assert isinstance(corr_df, pd.DataFrame)
        assert format in self.formats
        self.ensure_all_figures_closed()

        plt.figure(figsize=(7.5, 9))
        sns.heatmap(
            corr_df,
            annot=True,
            cmap="coolwarm",
            vmin=-1,
            vmax=1,
            square=True,
            linewidths=0.5,
            linecolor="black",
            clip_on=False,
            cbar_kws=dict(
                use_gridspec=False,
                location="bottom",
                orientation="horizontal",
                shrink=0.9,
            ),
        )
        plt.title("Correlation between questions")
        plt.xlabel("Question number")
        plt.ylabel("Question number")

        graph_bytes = self.get_graph_as_BytesIO(plt.gcf())
        self.ensure_all_figures_closed()

        if format == "bytes":
            return graph_bytes
        else:
            return self.get_graph_as_base64(graph_bytes)

    def histogram_of_grades_on_question_by_ta(
        self,
        question: int,
        ta_name: str,
        *,
        ta_df: Optional[pd.DataFrame] = None,
        versions: bool = False,
        format: str = "base64",
    ) -> Union[BytesIO, str]:
        """Generate a histogram of the grades on a specific question by a specific TA.

        Args:
            question: The question to generate the histogram for.
            ta_name: The name of the TA to generate the histogram for.

        Keyword Args:
            ta_df: Optional dataframe containing the ta data. Should be
                a copy or filtered version of self.ta_df. If omitted, defaults
                to None and self.ta_df is used.
            versions: Whether to split the histogram into versions. If omitted,
                defaults to False.
            format: The format to return the graph in. Should be either "base64"
                or "bytes". If omitted, defaults to "base64".

        Returns:
            Base64 encoded string or bytes containing the histogram.
        """
        if ta_df is None:
            ta_df = self.des._get_ta_data_for_ta(
                ta_name, self.des._get_ta_data_for_question(question_number=question)
            )

        assert isinstance(ta_df, pd.DataFrame)
        assert format in self.formats
        self.ensure_all_figures_closed()

        fig, ax = plt.subplots(figsize=(6.8, 4.2), tight_layout=True)
        bins = np.arange(ta_df["max_score"].max() + RANGE_BIN_OFFSET) - 0.5

        plot_series = []
        if versions is True:
            for version in range(1, round(ta_df["question_version"].max()) + 1):
                plot_series.append(
                    ta_df[(ta_df["question_version"] == version)]["score_given"]
                )
            labels = ["Version " + str(i) for i in range(1, len(plot_series) + 1)]
        else:
            plot_series.append(ta_df["score_given"])

        ax.hist(
            plot_series,
            bins=bins,
            ec="black",
            alpha=0.5,
        )
        ax.set_title("Grades for Q" + str(question) + " (by " + ta_name + ")")
        ax.set_xlabel("Mark given")
        ax.set_ylabel("# of times assigned")
        if versions is True:
            ax.legend(
                labels,
                loc="center left",
                bbox_to_anchor=(1, 0.5),
                ncol=1,
                fancybox=True,
            )

        plt.grid(True, alpha=0.5)

        graph_bytes = self.get_graph_as_BytesIO(fig)
        self.ensure_all_figures_closed()

        if format == "bytes":
            return graph_bytes
        else:
            return self.get_graph_as_base64(graph_bytes)

    def histogram_of_time_spent_marking_each_question(
        self,
        question_number: int,
        *,
        marking_times_df: Optional[pd.DataFrame] = None,
        versions: bool = False,
        max_time: int = 0,
        bin_width: int = 15,
        format: str = "base64",
    ) -> Union[BytesIO, str]:
        """Generate a histogram of the time spent marking a question.

        Args:
            question_number: The question to generate the histogram for.

        Keyword Args:
            marking_times_df: Optional dataframe containing the marking data. Should be
                a copy or filtered version of self.ta_df. If omitted, defaults
                to None and self.ta_df is used.
            versions: Whether to split the histogram into versions. If omitted,
                defaults to False.
            max_time: The maximum time to show on the histogram. If omitted,
                defaults to the maximum time in the "seconds_spent_marking" column
                of marking_times_df.
            bin_width: The width of each bin on the histogram. Should be given in
                units of seconds. If omitted, defaults to 15 seconds per bin.
            format: The format to return the graph in. Should be either "base64"
                or "bytes". If omitted, defaults to "base64".

        Returns:
            Base64 encoded string or bytes containing the histogram.
        """
        if marking_times_df is None:
            marking_times_df = self.ta_df()

        assert isinstance(marking_times_df, pd.DataFrame)

        if max_time == 0:
            max_time = round(max(marking_times_df["seconds_spent_marking"].div(60)))

        assert max_time > 0
        assert format in self.formats
        self.ensure_all_figures_closed()

        fig, ax = plt.subplots(figsize=(6.8, 4.2), tight_layout=True)
        bins = (np.arange(0, max_time + bin_width, bin_width) - (bin_width / 2)) / 60.0

        plot_series = []
        if versions is True:
            for version in range(
                1, round(marking_times_df["question_version"].max()) + 1
            ):
                plot_series.append(
                    marking_times_df[
                        (marking_times_df["question_number"] == question_number)
                    ][(marking_times_df["question_version"] == version)][
                        "seconds_spent_marking"
                    ].div(
                        60
                    )
                )
            labels = ["Version " + str(i) for i in range(1, len(plot_series) + 1)]
        else:
            plot_series.append(
                marking_times_df[
                    (marking_times_df["question_number"] == question_number)
                ]["seconds_spent_marking"].div(60)
            )

        ax.hist(
            plot_series,
            bins=bins,
            ec="black",
            alpha=0.5,
        )
        ax.set_title("Time spent marking Q" + str(question_number))
        ax.set_xlabel("Time spent (min)")
        ax.set_ylabel("# of papers")
        if versions is True:
            ax.legend(
                labels,
                loc="center left",
                bbox_to_anchor=(1, 0.5),
                ncol=1,
                fancybox=True,
            )
        plt.grid(True, alpha=0.5)

        graph_bytes = self.get_graph_as_BytesIO(fig)
        self.ensure_all_figures_closed()

        if format == "bytes":
            return graph_bytes
        else:
            return self.get_graph_as_base64(graph_bytes)

    def scatter_time_spent_vs_mark_given(
        self,
        question_number: int,
        times_spent_minutes: Union[List[int], List[List[float]]],
        marks_given: Union[List[int], List[List[float]]],
        *,
        versions: bool = False,
        format: str = "base64",
    ) -> Union[BytesIO, str]:
        """Generate a scatter plot of the time spent marking a question vs the mark given.

        Args:
            question_number: The question to generate the scatter plot for.
            times_spent_minutes: Listlike containing the marking times in minutes or
                a list of listlikes containing the marking times in minutes for each
                version.
            marks_given: Listlike containing the marks given or a list of listlikes
                containing the marks given for each version.

        Keyword Args:
            versions: Whether to split the scatter plot into versions. If omitted,
                defaults to False.
            format: The format to return the graph in. Should be either "base64"
                or "bytes". If omitted, defaults to "base64".

        Returns:
            Base64 encoded string or bytes containing the scatter plot.
        """
        assert format in self.formats
        self.ensure_all_figures_closed()

        fig, ax = plt.subplots(figsize=(6.8, 4.2), tight_layout=True)

        if versions is True:
            graphs = len(times_spent_minutes)
            assert graphs == len(marks_given)
            for i in range(0, graphs):
                ax.scatter(
                    marks_given[i],
                    times_spent_minutes[i],
                    ec="black",
                    alpha=0.5,
                    label="Version " + str(i + 1),
                )
        else:
            ax.scatter(
                marks_given,
                times_spent_minutes,
                ec="black",
                alpha=0.5,
                label="All versions",
            )

        ax.set_title("Q" + str(question_number) + ": Time spent vs Mark given")
        ax.set_ylabel("Time spent (min)")
        ax.set_xlabel("Mark given")
        if versions is True:
            ax.legend(loc="center left", bbox_to_anchor=(1, 0.5), ncol=1, fancybox=True)

        plt.grid(True, alpha=0.5)
        plt.xlim(
            left=-0.5, right=self.spec["question"][str(question_number)]["mark"] + 0.5
        )
        plt.ylim(bottom=-0.2)

        graph_bytes = self.get_graph_as_BytesIO(fig)
        self.ensure_all_figures_closed()

        if format == "bytes":
            return graph_bytes
        else:
            return self.get_graph_as_base64(graph_bytes)

    def boxplot_of_marks_given_by_ta(
        self,
        marks: List[List[int]],
        marker_names: List[str],
        question: int,
        *,
        format: str = "base64",
    ) -> Union[BytesIO, str]:
        """Generate a boxplot of the marks given by each TA for the specified question.

        The length and order of marks and marker_names should be the same such
        that marks[i] is the list of marks given by marker_names[i].

        Args:
            marks: The dataframe of marks to plot.
            marker_names: The names of the markers.
            question: The question to plot the boxplot for.

        Keyword Args:
            format: The format to return the graph in. Should be either "base64"
                or "bytes". If omitted, defaults to "base64".

        Returns:
            Base64 encoded string or bytes containing the boxplot.
        """
        assert len(marks) == len(marker_names)
        assert format in self.formats
        self.ensure_all_figures_closed()

        fig, ax = plt.subplots(figsize=(6.8, 4.2), tight_layout=True)

        # create boxplot and set colours
        for i, mark in reversed(list(enumerate(marks))):
            bp = ax.boxplot(mark, positions=[i], vert=False)
            self._boxplot_set_colors(bp, i / len(marks))
            (hL,) = plt.plot([], c=cm.hsv(i / len(marks)), label=marker_names[i])

        # set legend
        plt.legend(
            loc="center left",
            bbox_to_anchor=(1, 0.5),
            ncol=1,
            fancybox=True,
        )
        plt.grid(True, alpha=0.5)

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
                self.des._get_ta_data_for_question(question_number=question)[
                    "max_score"
                ].max(),
            ]
        )

        graph_bytes = self.get_graph_as_BytesIO(fig)
        self.ensure_all_figures_closed()

        if format == "bytes":
            return graph_bytes
        else:
            return self.get_graph_as_base64(graph_bytes)

    def _boxplot_set_colors(self, bp, colour):
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

    def line_graph_of_avg_marks_by_question(
        self, *, versions: bool = False, format: str = "base64"
    ) -> Union[BytesIO, str]:
        """Generate a line graph of the average percentage marks by question.

        Keyword Args:
            versions: Whether to split the line graph into versions. If omitted,
                defaults to False.
            format: The format to return the graph in. Should be either "base64"
                or "bytes". If omitted, defaults to "base64".

        Returns:
            Base64 encoded string or bytes containing the line graph.
        """
        assert format in self.formats
        self.ensure_all_figures_closed()

        plt.figure(figsize=(6.8, 4.2), tight_layout=True)

        if versions is True:
            averages = self.des.get_averages_on_all_questions_versions_as_percentage(
                overall=True
            )
            for i, v in enumerate(averages):
                if i == 0:
                    plt.plot(
                        range(1, self.spec["numberOfQuestions"] + 1),
                        v,
                        marker="o",
                        label="Overall",
                    )
                else:
                    plt.plot(
                        range(1, self.spec["numberOfQuestions"] + 1),
                        v,
                        marker="x",
                        label="Version " + str(i),
                    )
        else:
            plt.plot(
                range(1, self.spec["numberOfQuestions"] + 1),
                self.des.get_averages_on_all_questions_as_percentage(),
                marker="o",
                label="All versions",
            )
        if versions is True:
            plt.legend(
                loc="center left",
                bbox_to_anchor=(1, 0.5),
                ncol=1,
                fancybox=True,
            )
        plt.grid(True, alpha=0.5)
        plt.ylim([0, 100])
        plt.title("Average percentage by question")
        plt.xlabel("Question number")
        plt.ylabel("Average mark (%)")
        plt.xticks(range(1, self.spec["numberOfQuestions"] + 1))

        graph_bytes = self.get_graph_as_BytesIO(plt.gcf())
        self.ensure_all_figures_closed()

        if format == "bytes":
            return graph_bytes
        else:
            return self.get_graph_as_base64(graph_bytes)
