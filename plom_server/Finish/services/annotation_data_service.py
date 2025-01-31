# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Aden Chan
from __future__ import annotations

import csv
import io
from typing import List

from Mark.models.annotations import Annotation


class AnnotationDataService:
    """Service for the grabbing the full list of annotation data."""

    def get_csv_header(self) -> List:
        """Get the header for the csv file.

        Returns:
            List holding the header for the csv file. Contains TA marking information,
            paper, question and version info, timestamps and warnings.
        """
        keys = [
            "score",
            "marking_time",
            "marking_time_delta",
            "task",
            "user",
            "time_of_last_update",
            "rubrics",
            "paper_number",
        ]

        return keys

    def build_csv_data(self) -> List:
        """Get a list of all annotations in the database.

        Returns:
            List of dictionaries containing the annotation data for each annotation in the database.
        """
        annotations = Annotation.objects.all()
        data = []

        for annotation in annotations:
            data.append(
                {
                    "score": annotation.score,
                    "marking_time": annotation.marking_time,
                    "marking_time_delta": annotation.marking_delta_time,
                    "task": annotation.task,
                    "user": annotation.user,
                    "time_of_last_update": annotation.time_of_last_update,
                    "rubrics": [rubric.rid for rubric in annotation.rubric_set.all()],
                    "paper_number": annotation.task.paper.paper_number,
                }
            )

        return data

    def get_csv_data_as_string(self) -> str:
        """Get the csv data as a string.

        Returns:
            The csv data as a string.
        """
        data = self.build_csv_data()
        keys = self.get_csv_header()

        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=keys)
        writer.writeheader()

        for row in data:
            writer.writerow(row)

        return output.getvalue()
