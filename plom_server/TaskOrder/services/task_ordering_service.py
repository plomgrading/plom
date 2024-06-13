# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Julian Lapenna
# Copyright (C) 2023 Edith Coates
# Copyright (C) 2024 Colin B. Macdonald
# Copyright (C) 2024 Bryan Tanady

from __future__ import annotations

from Mark.models import MarkingTask
from Mark.services import marking_priority
from Papers.services import SpecificationService


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

    def get_task_priorities(self, status: bool):
        """Get the task priorities dict and list of not fully marked papers.

        Args:
            status: set to true to include MarkingTask.status in the return.

        Returns:
            if status is set to true it returns a mapping
            from a tuple of (paper_number, q_index) to a tuple
            of (priority, MarkingTask.StatusChoices). Otherwise it will be mapped
            to only the task priority.

        Note: MarkingTask.StatusChoices are represented as Integers, where:
            1 represents TO_DO.
            2 represents OUT.
            3 represents COMPLETE.
            4 represents OUT_OF_DATE.
        """
        if status:
            _marking_tasks = MarkingTask.objects.all()

        else:
            _marking_tasks = MarkingTask.objects.filter(status=MarkingTask.TO_DO)

        _marking_tasks.select_related("paper")
        marking_tasks = list(
            _marking_tasks.order_by("paper__paper_number", "question_index")
        )

        task_priorities = {}
        marking_task_list = list()

        for mt in marking_tasks:
            if status:
                mapped_value = (mt.marking_priority, mt.status)
            else:
                mapped_value = mt.marking_priority

            task_priorities[(mt.paper.paper_number, mt.question_index)] = mapped_value
            marking_task_list.append(mt.paper.paper_number)

        return task_priorities, marking_task_list

    def get_paper_number_to_priority_list(self) -> dict[int, list[int, int]]:
        """Get the mapping from a paper number to the list of (priority, status).

        If a marking task is missing, it will be flagged with (-1, -1).

        Returns:
            A dictionary that maps paper number to the list of tuples of
            (priority, status), where the list is sorted in asceding order
            by question index.
        """
        task_priorities, marking_task_list = self.get_task_priorities(status=True)
        total_questions = SpecificationService.get_n_questions()
        missing_flag = (-1, -1)

        paper_to_priority_and_status_list = dict()

        for paper_number in marking_task_list:
            paper_to_priority_and_status_list[paper_number] = [
                task_priorities.get((paper_number, q_idx), missing_flag)
                for q_idx in range(1, total_questions + 1)
            ]
        return paper_to_priority_and_status_list

    def get_csv_header(self) -> list[str]:
        """Get the CSV header for the task priorities."""
        return ["Paper Number", "Question Number", "Priority Value"]

    def get_task_priorities_download(self) -> list[dict[str, int]]:
        """Get the task priorities for download."""
        task_priorities = self.get_task_priorities(status=False)[0]
        return [
            {
                "Paper Number": paper_number,
                "Question Number": question_idx,
                "Priority Value": priority,
            }
            for (paper_number, question_idx), priority in task_priorities.items()
        ]

    def handle_file_upload(self, csv_data) -> dict[tuple[int, int], int]:
        """Handle uploaded file data of task priorities.

        Args:
            csv_data: The CSV data.

        Returns:
            A dictionary of task priorities, keyed by
            (paper_number, question_index) pairs.
        """
        custom_priorities = {}
        for row in csv_data:
            key = (int(row[0]), int(row[1]))
            custom_priorities[key] = int(row[2])

        return custom_priorities
