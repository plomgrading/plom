# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Julian Lapenna
# Copyright (C) 2023-2024 Andrew Rechnitzer
# Copyright (C) 2024-2025 Colin B. Macdonald

import csv
from io import StringIO

import arrow

from plom_server.Mark.services import MarkingTaskService


class TaMarkingService:
    """Service for the TA marking information."""

    def get_csv_header(self) -> list:
        """Get the header for the csv file.

        Returns:
            List holding the header for the csv file. Contains TA marking information,
            paper, question and version info, timestamps and warnings.
        """
        keys = [
            "user",
            "paper_number",
            "question_index",
            "question_version",
            "score_given",
            "max_score",
            "seconds_spent_marking",
            "last_update_time",
        ]

        return keys

    def build_csv_data(self) -> list:
        """Get information about the latest annotation for all marking tasks that are complete.

        Returns:
            List where each element is a dict keyed by str, representing a single annotation.

        Raises:
            None expected
        """
        complete_marking_tasks = (
            MarkingTaskService()
            .get_complete_marking_tasks()
            .prefetch_related("paper", "latest_annotation", "latest_annotation__user")
            .order_by(
                "latest_annotation__user__username",
                "paper__paper_number",
                "question_index",
            )
        )
        csv_data = []
        for task in complete_marking_tasks:
            assert task.latest_annotation.user is not None
            assert task.latest_annotation.annotation_data is not None
            csv_data.append(
                {
                    "user": task.latest_annotation.user.username,
                    "paper_number": task.paper.paper_number,
                    "question_index": task.question_index,
                    "question_version": task.question_version,
                    "score_given": task.latest_annotation.score,
                    "max_score": task.latest_annotation.annotation_data["maxMark"],
                    "seconds_spent_marking": task.latest_annotation.marking_time,
                    "last_update_time": arrow.get(task.last_update).isoformat(
                        " ", "seconds"
                    ),
                }
            )

        return csv_data

    def build_ta_info_csv_as_string(self) -> str:
        """Constructs TA info csv and casts it to a string."""
        ta_info = self.build_csv_data()
        keys = self.get_csv_header()
        csv_io = StringIO()
        w = csv.DictWriter(csv_io, keys, extrasaction="ignore")
        w.writeheader()
        w.writerows(ta_info)
        csv_io.seek(0)

        return csv_io.getvalue()
