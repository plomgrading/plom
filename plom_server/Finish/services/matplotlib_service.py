# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Julian Lapenna

from typing import Optional

import matplotlib
import matplotlib.pyplot as plt
import pandas as pd

from Finish.services import GraphingDataService
from Papers.models import Specification


RANGE_BIN_OFFSET = 2


class MatplotlibService:
    """Service for generating matplotlib plots from data."""

    matplotlib.use("Pdf")

    def __init__(self):
        gds = GraphingDataService()
        self.spec = Specification.load().spec_dict

        self.student_df = gds.get_student_data()
        self.ta_df = gds.get_ta_data()

    def check_num_figs(self):
        if len(plt.get_fignums()) > 0:
            print("Warn: ", len(plt.get_fignums()), " figures open.")

    def histogram_of_total_marks(self, student_df: Optional[pd.DataFrame] = None):
        """Generate a histogram of the total marks.

        Args:
            student_df: Optional dataframe containing the student data. Should be
                a copy or filtered version of self.student_df. If omitted, defaults
                to None and self.student_df is used.
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
