# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Julian Lapenna
# Copyright (C) 2023 Edith Coates
# Copyright (C) 2024 Colin B. Macdonald

from __future__ import annotations

from Mark.models import MarkingTask
from Mark.services import marking_priority


class TaskOrderService:
    """Class for handling task ordering."""

    def update_priority_ordering(
        self,
        order: str,
        *,
        custom_order: None | dict[tuple[int, int], int] = None,
    ) -> None:
        """Update the priority ordering of tasks."""
        if order == "shuffle":
            marking_priority.set_marking_piority_shuffle()
        elif order == "custom":
            assert custom_order is not None, "must provide custom_order kwarg"
            marking_priority.set_marking_priority_custom(custom_order=custom_order)
        else:
            marking_priority.set_marking_priority_paper_number()

    def get_task_priorities(self) -> dict[tuple[int, int], int]:
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

    def get_csv_header(self) -> list[str]:
        """Get the CSV header for the task priorities."""
        return ["Paper Number", "Question Number", "Priority Value"]

    def get_task_priorities_download(self) -> list[dict[str, int]]:
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

    def handle_file_upload(self, csv_data) -> dict[tuple[int, int], int]:
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
