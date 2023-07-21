# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Julian Lapenna

import base64
from io import BytesIO
from typing import Optional

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from Finish.services import StudentMarkService, TaMarkingService
from Mark.services import MarkingTaskService
from Papers.models import Specification


class GraphingDataService:
    """Service for getting data to graph."""

    def __init__(self):
        self.sms = StudentMarkService()
        self.tms = TaMarkingService()
        self.mts = MarkingTaskService()
        self.spec = Specification.load().spec_dict

        student_dict = self.sms.get_all_students_download(
            version_info=True, timing_info=False, warning_info=False
        )
        student_keys = self.sms.get_csv_header(
            self.spec, version_info=True, timing_info=False, warning_info=False
        )
        self.student_df = pd.DataFrame(student_dict, columns=student_keys)

        ta_dict = self.tms.build_csv_data()
        ta_keys = self.tms.get_csv_header()

        self.ta_df = pd.DataFrame(ta_dict, columns=ta_keys)

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

    def get_ta_data(self) -> pd.DataFrame:
        """Return the dataframe of TA data."""
        return self.ta_df

    def get_student_data(self) -> pd.DataFrame:
        """Return the dataframe of student data."""
        return self.student_df

    def get_total_average_mark(self) -> float:
        """Return the average total mark for all students as a float."""
        return self.student_df["total_mark"].mean()

    def get_total_median_mark(self) -> float:
        """Return the median total mark for all students as a float."""
        return self.student_df["total_mark"].median()

    def get_total_stdev_mark(self) -> float:
        """Return the standard deviation of the total marks for all students as a float."""
        return self.student_df["total_mark"].std()

    def get_total_marks(self) -> list:
        """Return the total marks for all students as a list."""
        return self.student_df["total_mark"].tolist()

    def get_marks_for_all_questions(self, student_df: pd.DataFrame) -> pd.DataFrame:
        """Get the marks for each question as a dataframe.

        Args:
            student_df: The dataframe containing the student data. Should be
                a copy or filtered version of self.student_df.

        Returns:
            A dataframe containing the marks for each question.
        """
        return student_df.filter(regex="q[0-9]*_mark")

    def get_question_correlation_heatmap(
        self, student_df: Optional[pd.DataFrame] = None
    ) -> pd.DataFrame:
        """Get the correlation heatmap for the questions.

        Args:
            student_df: Optional dataframe containing the student data. Should be
                a copy or filtered version of self.student_df. If omitted, defaults
                to None and self.student_df is used.

        Returns:
            pd.DataFrame: A dataframe containing the correlation heatmap.
        """
        if not student_df:
            student_df = self.student_df

        marks_corr = (
            student_df.filter(regex="q[0-9]*_mark").corr(numeric_only=True).round(2)
        )

        for i, name in enumerate(marks_corr.columns):
            marks_corr.rename({name: "Q" + str(i + 1)}, axis=1, inplace=True)
            marks_corr.rename({name: "Q" + str(i + 1)}, axis=0, inplace=True)

        return marks_corr

    def get_ta_data_for_ta(self, ta_name: str, ta_df: pd.DataFrame) -> pd.DataFrame:
        """Get the dataframe of TA marking for a specific TA.

        Args:
            ta_name: The TA to get the data for.
            ta_df: The dataframe containing the TA data. Should be a copy or
                filtered version of self.ta_df.

        Returns:
            A dataframe containing the TA data for the specified TA.
        """
        marks = ta_df[ta_df["user"] == ta_name]
        marks.name = ta_name
        return marks

    def get_all_ta_data_by_ta(self) -> dict:
        """Get TA marking data for all TAs.

        Returns:
            A dictionary keyed by the (str) TA name, containing the (pd.Dataframe)
            marking data for each TA.
        """
        marks_by_ta = {}
        for ta_name in self.ta_df["user"].unique():
            marks_by_ta[ta_name] = self.get_ta_data_for_ta(ta_name, self.ta_df)
        return marks_by_ta

    def get_ta_data_for_question(
        self, question_number: int, ta_df: pd.DataFrame
    ) -> pd.DataFrame:
        """Get the dataframe of TA marking data for a specific question.

        Args:
            question_number: The question to get the data for.
            ta_df: The dataframe containing the TA data. Should be a copy or
                filtered version of self.ta_df.

        Returns:
            A dataframe containing the TA data for the specified question.
        """
        times = ta_df[ta_df["question_number"] == question_number]
        times.name = question_number
        return times

    def get_times_for_all_questions(self) -> dict:
        """Get the marking times for all questions.

        Returns:
            A dictionary keyed by the (int) question number, containing the
            (pd.Series) marking times for all questions.
        """
        times_by_question = {}
        for question in self.spec["question"]:
            q = int(question)
            times_by_question[q] = self.get_ta_data_for_question(q, self.ta_df)[
                "seconds_spent_marking"
            ]
        return times_by_question

    def get_questions_marked_by_this_ta(
        self, ta_name: str, ta_df: pd.DataFrame
    ) -> list:
        """Get the questions that were marked by a specific TA.

        Args:
            ta_name: The TA to get the data for.
            ta_df: The dataframe containing the TA data. Should be a copy or
                filtered version of self.ta_df.

        Returns:
            A list of questions marked by the specified TA.
        """
        return ta_df[ta_df["user"] == ta_name]["question_number"].unique().tolist()
