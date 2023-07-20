# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Julian Lapenna

import numpy as np
import pandas as pd

from Finish.services import StudentMarkService, TaMarkingService
from Mark.models import MarkingTask
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
            version_info=True, timing_info=True, warning_info=False
        )
        student_keys = self.sms.get_csv_header(
            self.spec, version_info=True, timing_info=True, warning_info=False
        )
        self.student_df = pd.DataFrame(student_dict, columns=student_keys)

        ta_dict = self.tms.build_csv_data()
        ta_keys = self.tms.get_csv_header()

        self.ta_df = pd.DataFrame(ta_dict, columns=ta_keys)

    def get_total_average_mark(self) -> float:
        """Return the average total mark for all students as a float."""
        return self.student_df["total_mark"].mean()

    def get_total_median_mark(self) -> float:
        """Return the median total mark for all students as a float."""
        return self.student_df["total_mark"].median()

    def get_total_stdev_mark(self) -> float:
        """Return the standard deviation of the total marks for all students as a float."""
        return self.student_df["total_mark"].std()
