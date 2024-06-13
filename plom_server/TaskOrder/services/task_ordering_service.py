# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Julian Lapenna
# Copyright (C) 2023 Edith Coates
# Copyright (C) 2024 Colin B. Macdonald

from __future__ import annotations

from Mark.models import MarkingTask
from Mark.services import marking_priority
from Papers.services import SpecificationService
from typing import Tuple, Dict, List


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

    def _get_task_priorities(self):
        """Get the task priorities dict and list of not fully marked papers.

        Returns:
            A dictionary of task priorities, keyed by
            (paper_number, question_index) pairs and a list of paper_number
            for papers that have not been fully marked.
        """
        _marking_tasks = MarkingTask.objects.filter(
            status=MarkingTask.TO_DO
        ).select_related("paper")
        marking_tasks = list(
            _marking_tasks.order_by("paper__paper_number", "question_index")
        )

        task_priorities = {}
        unfinished_paper = []

        for mt in marking_tasks:
            task_priorities[(mt.paper.paper_number, mt.question_index)] = (
                mt.marking_priority
            )
            unfinished_paper.append(mt.paper.paper_number)

        return task_priorities, unfinished_paper

    def get_paper_number_to_priority_list(self) -> dict[int, list[int]]:
        """Get the mapping from a paper number to the list of priorities.

        The paper that has been fully marked will not be recorded here.
        Additionally, the questions that have been marked will have priority
        of 0.

        Returns:
            A dictionary mapping paper number to the list of priorities
            for that paper sorted by question index.
        """

        task_priorities, unfinished_paper = self._get_task_priorities()
        total_questions = SpecificationService.get_n_questions()

        paper_to_priority_map = dict()

        for paper_number in unfinished_paper:
            priority_list = [
                task_priorities.get((paper_number, q_idx), 0)
                for q_idx in range(1, total_questions + 1)
            ]
            paper_to_priority_map[paper_number] = priority_list
            return paper_to_priority_map

    def get_csv_header(self) -> list[str]:
        """Get the CSV header for the task priorities."""
        return ["Paper Number", "Question Number", "Priority Value"]

    def get_task_priorities_download(self) -> list[dict[str, int]]:
        """Get the task priorities for download."""
        task_priorities = self.get_task_priorities()
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
