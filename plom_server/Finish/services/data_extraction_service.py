# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Julian Lapenna
# Copyright (C) 2023-2025 Colin B. Macdonald
# Copyright (C) 2024 Bryan Tanady
# Copyright (C) 2024 Andrew Rechnitzer
# Copyright (C) 2025 Aden Chan

import pandas as pd

from . import StudentMarkService, TaMarkingService
from plom_server.Papers.services import SpecificationService


class DataExtractionService:
    """Service for getting pulling data from the database.

    Warning: Many methods return dataframes, so the caller should have pandas installed
    or only use methods that return other data types. See method type hints for more
    details.

    Upon instantiation, the service pulls data from the database. It does not refresh
    the data, so it is recommended to create a new instance of the service if the
    data in the database has changed.

    Pandas dataframes are used to store the data. The original dataframes can be
    accessed using the `get_ta_data` and `get_student_data` methods.
    """

    def __init__(self):
        student_dict = StudentMarkService.get_all_marking_info_faster()
        student_keys = StudentMarkService._get_csv_header()
        self.student_df = pd.DataFrame(student_dict, columns=student_keys)

        tms = TaMarkingService()
        ta_dict = tms.build_csv_data()
        ta_keys = tms.get_csv_header()
        self.ta_df = pd.DataFrame(ta_dict, columns=ta_keys)

    def _get_ta_data(self) -> pd.DataFrame:
        """Return the dataframe of TA data.

        Warning: caller will need pandas installed as this method returns a dataframe.
        """
        return self.ta_df

    def _get_student_data(self) -> pd.DataFrame:
        """Return the dataframe of student data.

        Warning: caller will need pandas installed as this method returns a dataframe.
        """
        return self.student_df

    def get_student_data(self) -> pd.DataFrame:
        """Return a copy dataframe of student data (safe copying to maintain encapsulation).

        Warning: caller will need pandas installed as this method returns a dataframe.
        """
        return self.student_df.copy()

    def get_descriptive_statistics_of_total(self) -> dict[str, float]:
        """Return descriptive statistics about the totals for the assessment.

        Gives dict of count, max, min, median, mean, mode, stddev, percentile25, percentile75.
        """
        return {
            "count": self.student_df["Total"].count(),
            "max": self.student_df["Total"].max(),
            "percentile75": self.student_df["Total"].quantile(0.75),
            "median": self.student_df["Total"].median(),
            "percentile25": self.student_df["Total"].quantile(0.25),
            "min": self.student_df["Total"].min(),
            "mean": self.student_df["Total"].mean(),
            "mode": self.student_df["Total"].mode(),
            "stddev": self.student_df["Total"].std(),
        }

    def get_descriptive_statistics_of_question(
        self, question_index: int
    ) -> dict[str, float]:
        """Return descriptive statistics about the totals for the assessment.

        Gives dict of count, max, min, median, mean, mode, stddev, percentile25, percentile75.
        """
        qlabel = SpecificationService.get_question_label(question_index)
        qs = f"{qlabel}_mark"
        return {
            "count": self.student_df[qs].count(),
            "max": self.student_df[qs].max(),
            "percentile75": self.student_df[qs].quantile(0.75),
            "median": self.student_df[qs].median(),
            "percentile25": self.student_df[qs].quantile(0.25),
            "min": self.student_df[qs].min(),
            "mean": self.student_df[qs].mean(),
            "mode": self.student_df[qs].mode(),
            "stddev": self.student_df[qs].std(),
        }

    def get_totals_average(self) -> float:
        """Return the average of the total mark over all students as a float."""
        return self.student_df["Total"].mean()

    def get_totals_median(self) -> float:
        """Return the median of the total mark over all students as a float."""
        return self.student_df["Total"].median()

    def get_totals_stdev(self) -> float:
        """Return the standard deviation of the total mark over all students as a float."""
        return self.student_df["Total"].std()

    def get_totals(self) -> list[int]:
        """Return the total mark for each student as a list.

        No particular order is promised: useful for statistics for example.
        """
        self.student_df.dropna(subset=["Total"], inplace=True)
        return self.student_df["Total"].tolist()

    def _get_average_on_question_as_percentage(self, qidx: int) -> float:
        """Return the average mark on a specific question as a percentage."""
        qlabel = SpecificationService.get_question_label(qidx)
        maxmark = SpecificationService.get_question_max_mark(qidx)
        return 100 * self.student_df[f"{qlabel}_mark"].mean() / maxmark

    def _get_average_on_question_version_as_percentage(
        self, question_index: int, version_number: int
    ) -> float:
        """Return the average mark on a specific question as a percentage."""
        qlabel = SpecificationService.get_question_label(question_index)
        maxmark = SpecificationService.get_question_max_mark(question_index)
        version_df = self.student_df[
            (self.student_df[f"{qlabel}_version"] == version_number)
        ]
        return 100 * version_df[f"{qlabel}_mark"].mean() / maxmark

    def get_averages_on_all_questions_as_percentage(self) -> list[float]:
        """Return the average mark on each question as a percentage."""
        averages = []
        for q in SpecificationService.get_question_indices():
            averages.append(self._get_average_on_question_as_percentage(q))
        return averages

    def get_averages_on_all_questions_versions_as_percentage(
        self, *, overall: bool = False
    ) -> list[list[float]]:
        """Return the average mark on each question as a percentage.

        Keyword Args:
            overall: If True, the overall average for all questions is returned as the first
                element in the list.

        Returns:
            A list of lists of floats. The first list contains the averages for
            all questions. The remaining lists contain the averages for each
            question version.
        """
        averages = []

        if overall:
            averages.append(self.get_averages_on_all_questions_as_percentage())

        for v in SpecificationService.get_list_of_versions():
            _averages = []
            for q in SpecificationService.get_question_indices():
                _averages.append(
                    self._get_average_on_question_version_as_percentage(q, v)
                )
            averages.append(_averages)

        return averages

    def _get_average_grade_on_question(self, qlabel: str) -> float:
        """Return the average grade on a specific question (not percentage)."""
        return self.student_df[f"{qlabel}_mark"].mean()

    def get_average_grade_on_all_questions(self) -> list[tuple[int, str, float]]:
        """Return the average grade on each question (not percentage)."""
        averages = []
        for qidx, qlabel in SpecificationService.get_question_index_label_pairs():
            averages.append((qidx, qlabel, self._get_average_grade_on_question(qlabel)))
        return averages

    def _get_marks_for_all_questions(
        self, *, student_df: pd.DataFrame | None = None
    ) -> pd.DataFrame:
        """Get the marks for each question as a dataframe.

        Warning: caller will need pandas installed as this method returns a dataframe.

        Keyword Args:
            student_df: Optional dataframe containing the student data. Should be
                a copy or filtered version of self.student_df. If omitted,
                self.student_df is used.

        Returns:
            A dataframe containing the marks for each question.
        """
        if student_df is None:
            student_df = self.student_df
        assert isinstance(student_df, pd.DataFrame)

        return student_df.filter(regex=".*_mark")

    def _get_question_correlation_heatmap_data(
        self, *, student_df: pd.DataFrame | None = None
    ) -> pd.DataFrame:
        """Get the correlation heatmap data for the questions.

        Warning: caller will need pandas installed as this method returns a dataframe.

        Keyword Args:
            student_df: Optional dataframe containing the student data. Should be
                a copy or filtered version of self.student_df. If omitted,
                self.student_df is used.

        Returns:
            A dataframe containing the correlation heatmap.
        """
        if student_df is None:
            student_df = self.student_df
        assert isinstance(student_df, pd.DataFrame)

        marks_corr = student_df.filter(regex=".*_mark").corr(numeric_only=True).round(2)

        for i, name in enumerate(marks_corr.columns):
            qlabel_only = name.removesuffix("_mark")
            marks_corr.rename({name: qlabel_only}, axis=1, inplace=True)
            marks_corr.rename({name: qlabel_only}, axis=0, inplace=True)

        return marks_corr

    def _get_ta_data_for_ta(
        self, ta_name: str, *, ta_df: pd.DataFrame | None = None
    ) -> pd.DataFrame:
        """Get the dataframe of TA marking data for a specific TA.

        Warning: caller will need pandas installed as this method returns a dataframe.

        Args:
            ta_name: The TA to get the data for.

        Keyword Args:
            ta_df: The dataframe containing the TA data. Should be a copy or
                filtered version of self.ta_df. If omitted, self.ta_df is used.

        Returns:
            A dataframe containing the TA data for the specified TA.
        """
        if ta_df is None:
            ta_df = self.ta_df
        assert isinstance(ta_df, pd.DataFrame)
        marks = ta_df[ta_df["user"] == ta_name]
        return marks

    def _get_all_ta_data_by_ta(self) -> dict[str, pd.DataFrame]:
        """Get TA marking data for all TAs.

        Warning: caller will need pandas installed as this method returns a dataframe.

        Returns:
            A dictionary keyed by the TA name, containing the marking
            data for each TA.
        """
        marks_by_ta = {}
        for ta_name in self.ta_df["user"].unique():
            marks_by_ta[ta_name] = self._get_ta_data_for_ta(ta_name)
        return marks_by_ta

    def _get_ta_data_for_question(
        self, qidx: int, *, ta_df: pd.DataFrame | None = None
    ) -> pd.DataFrame:
        """Get the dataframe of TA marking data for a specific question.

        Warning: caller will need pandas installed as this method returns a dataframe.

        Args:
            qidx: The question to get the data for.

        Keyword Args:
            ta_df: Optional dataframe containing the TA data. Should be a copy or
                filtered version of self.ta_df. If omitted, self.ta_df is used.

        Returns:
            A dataframe containing the TA data for the specified question.
        """
        if ta_df is None:
            ta_df = self.ta_df
        assert isinstance(ta_df, pd.DataFrame)

        question_df = ta_df[ta_df["question_index"] == qidx]
        return question_df

    def _get_all_ta_data_by_qidx(self) -> dict[int, pd.DataFrame]:
        """Get TA marking data for all questions as a dict.

        Warning: caller will need pandas installed as this method returns a dataframe.

        Returns:
            A dictionary keyed by the question index, containing the
            marking data for each question.  The keys in the results are
            sorted by question index (that is, iterating on the return
            value will be sorted by question index b/c Python 3 preserves
            insertion order).
        """
        marks_by_question = {}
        for qidx in sorted(self.ta_df["question_index"].unique()):
            marks_by_question[qidx] = self._get_ta_data_for_question(qidx)
        return marks_by_question

    def _get_times_for_all_questions(self) -> dict[int, pd.Series]:
        """Get the marking times for all questions.

        Warning: caller will need pandas installed as this method returns a pandas series.

        Returns:
            A dictionary keyed by the question indices, containing the
            marking times for each question.
        """
        times_by_question = {}
        for qi in self.ta_df["question_index"].unique():
            times_by_question[qi] = self._get_ta_data_for_question(qi)[
                "seconds_spent_marking"
            ]
        return times_by_question

    def get_questions_marked_by_this_ta(
        self, ta_name: str, *, ta_df: pd.DataFrame | None = None
    ) -> list[int]:
        """Get the questions that were marked by a specific TA.

        Args:
            ta_name: The TA to get the data for.

        Keyword Args:
            ta_df: The dataframe containing the TA data. Should be a copy or
                filtered version of self.ta_df. If omitted, self.ta_df is used.

        Returns:
            A list of questions marked by the specified TA.
        """
        if ta_df is None:
            ta_df = self.ta_df
        assert isinstance(ta_df, pd.DataFrame)

        return (
            ta_df[ta_df["user"] == ta_name]["question_index"]
            .drop_duplicates()
            .sort_values()
            .tolist()
        )

    def get_tas_that_marked_this_question(
        self, question_index: int, *, ta_df: pd.DataFrame | None = None
    ) -> list[str]:
        """Get the TAs that marked a specific question.

        Args:
            question_index: The question to get the data for.

        Keyword Args:
            ta_df: The dataframe containing the TA data. Should be a copy or
                filtered version of self.ta_df. If omitted, self.ta_df is used.

        Returns:
            A list of TA names that marked the specified question.
        """
        if ta_df is None:
            ta_df = self.ta_df
        assert isinstance(ta_df, pd.DataFrame)

        users = ta_df[(ta_df["question_index"] == question_index)]["user"]
        user_list = users.unique().tolist()
        # MyPy complains about types (on CI, not locally) unsure why so assert
        assert isinstance(user_list, list)
        for x in user_list:
            assert isinstance(x, str)
        return user_list

    def _get_scores_for_qidx(
        self,
        qidx: int,
        *,
        ver: int | None = None,
    ) -> list[float]:
        """Get the marks assigned for a specific question.

        Args:
            qidx: The question to get the data for.

        Keyword Args:
            ver: which version, or if omitted/None then report for all.

        Returns:
            A list of marks assigned for the specified question / version.
        """
        df = self.ta_df
        assert isinstance(df, pd.DataFrame)

        if ver is not None:
            tmp = df[(df["question_index"] == qidx) & (df["question_version"] == ver)]
        else:
            tmp = df[df["question_index"] == qidx]
        return tmp["score_given"].tolist()

    def _get_marking_times_for_qidx(
        self,
        qidx: int,
        *,
        ver: int | None = None,
    ) -> list[float]:
        """Get the marking times for a specific question.

        Args:
            qidx: The question to get the data for.

        Keyword Args:
            ver: which version, or if omitted/None then report for all.

        Returns:
            A list of marks assigned for the specified question / version.
        """
        df = self.ta_df
        assert isinstance(df, pd.DataFrame)

        if ver is not None:
            tmp = df[(df["question_index"] == qidx) & (df["question_version"] == ver)]
        else:
            tmp = df[df["question_index"] == qidx]
        return tmp["seconds_spent_marking"].tolist()

    def get_scores_for_ta(
        self, ta_name: str, *, ta_df: pd.DataFrame | None = None
    ) -> list[float]:
        """Get the marks assigned for by a specific TA.

        Args:
            ta_name: The TA to get the data for.

        Keyword Args:
            ta_df: Optional dataframe containing the TA data. Should be a copy or
                filtered version of self.ta_df. If omitted, self.ta_df is used.

        Returns:
            A list of marks assigned by the specified TA.
        """
        if ta_df is None:
            ta_df = self.ta_df
        assert isinstance(ta_df, pd.DataFrame)

        return ta_df[ta_df["user"] == ta_name]["score_given"].tolist()
