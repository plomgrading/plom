# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Julian Lapenna
# Copyright (C) 2023 Edith Coates

import csv
from io import StringIO
from typing import Dict, Union

from Mark.models import MarkingTask
from Mark.services import MarkingTaskService


class TaskOrderService:
    """Class for handling task ordering."""

    def update_priority_ordering(
        self,
        order: str,
        *,
        custom_order: Union[Dict[tuple[int, int], int], None] = None,
    ):
        """Update the priority ordering of tasks."""
        mts = MarkingTaskService()
        mts.set_task_priorities(order_by=order, custom_order=custom_order)

    def get_task_priorities(self) -> dict:
        """Get the task priorities.

        Returns:
            A dictionary of task priorities, keyed by
            (paper_number, question_number) pairs.
        """
        _marking_tasks = MarkingTask.objects.filter(
            status=MarkingTask.TO_DO
        ).select_related("paper")
        marking_tasks = list(
            _marking_tasks.order_by("paper__paper_number", "question_number")
        )

        task_priorities = {}
        for mt in marking_tasks:
            task_priorities[
                (mt.paper.paper_number, mt.question_number)
            ] = mt.marking_priority

        return task_priorities

    def get_csv_header(self) -> list:
        """Get the CSV header for the task priorities."""
        return ["Paper Number", "Question Number", "Priority Value"]

    def get_task_priorities_download(self) -> list:
        """Get the task priorities for download."""
        task_priorities = self.get_task_priorities()
        return [
            {
                "Paper Number": paper_number,
                "Question Number": question_number,
                "Priority Value": priority,
            }
            for (paper_number, question_number), priority in task_priorities.items()
        ]

    def handle_file_upload(self, csv_data) -> Dict[tuple[int, int], int]:
        """Handle uploaded file data of task priorities.

        Args:
            csv_data: The CSV data.

        Returns:
            A dictionary of task priorities, keyed by
            (paper_number, question_number) pairs.
        """
        custom_priorities = {}
        for row in csv_data:
            key = (int(row[0]), int(row[1]))
            custom_priorities[key] = int(row[2])

        return custom_priorities
