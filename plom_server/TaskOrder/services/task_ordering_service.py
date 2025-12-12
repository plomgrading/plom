# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Julian Lapenna
# Copyright (C) 2023 Edith Coates
# Copyright (C) 2024-2025 Colin B. Macdonald
# Copyright (C) 2024-2025 Bryan Tanady
# Copyright (C) 2025 Aidan Murphy

from csv import DictReader

from plom_server.Mark.models import MarkingTask
from plom_server.Mark.services import MarkingPriorityService
from plom_server.Papers.services import SpecificationService


class TaskOrderService:
    """Class for handling task ordering.

    See also the closely-related
    :py:`plom_server.Mark.services.MarkingPriorityService`.
    """

    # TODO: consider move to MarkingPriorityService?
    @staticmethod
    def update_priority_ordering(
        order: str,
        *,
        custom_order: None | dict[tuple[int, int], int | float] = None,
    ) -> None:
        """Update the priority ordering of tasks.

        Args:
            order: one of "shuffle", "paper_number", or "custom".

        Keyword Args:
            custom_order: a dictionary specifying a custom task ordering
                (for existing tasks).
        """
        if order == "shuffle":
            MarkingPriorityService.set_marking_priority_shuffle()
        elif order == "custom":
            assert custom_order is not None, "must provide custom_order kwarg"
            MarkingPriorityService.set_marking_priority_custom(
                custom_order=custom_order
            )
        else:
            MarkingPriorityService.set_marking_priority_paper_number()

    @staticmethod
    def _get_task_priorities() -> (
        tuple[dict[tuple[int, int], tuple[float, str]], set[int]]
    ):
        """Get the task priorities dict and set of paper numbers in MarkingTask.

        Returns:
            Mapping from a tuple of (paper_number, q_index) to a tuple
            of (priority, MarkingTask's status (str)), and a set of paper numbers
            for papers found in MarkingTask.
        """
        marking_tasks = (
            MarkingTask.objects.exclude(status=MarkingTask.OUT_OF_DATE)
            .select_related("paper")
            .order_by("paper__paper_number", "question_index")
        )

        task_priorities = {}
        paper_numbers = set()

        for mt in marking_tasks:
            mapped_value = (mt.marking_priority, mt.get_status_display())
            task_priorities[(mt.paper.paper_number, mt.question_index)] = mapped_value
            paper_numbers.add(mt.paper.paper_number)

        return task_priorities, paper_numbers

    @classmethod
    def get_paper_number_to_priority_list(
        cls,
    ) -> dict[int, list[tuple[float, str] | tuple[None, str]]]:
        """Get the mapping from a paper number to the list of (priority, status).

        If a marking task is missing, it will be flagged
        with (None, "Missing").

        Returns:
            A dictionary that maps paper number to the list of tuples of
            (priority, status), where the list is sorted in ascending order
            by question index.
        """
        task_priorities, paper_numbers = cls._get_task_priorities()
        total_questions = SpecificationService.get_n_questions()
        missing_flag = (None, "Missing")

        paper_to_priority_and_status_list = dict()

        for paper_number in paper_numbers:
            paper_to_priority_and_status_list[paper_number] = [
                task_priorities.get((paper_number, q_idx), missing_flag)
                for q_idx in range(1, total_questions + 1)
            ]
        return paper_to_priority_and_status_list

    @staticmethod
    def get_csv_header() -> list[str]:
        """Get the CSV header for the task priorities."""
        return ["Paper Number", "Question Index", "Priority Value", "Status"]

    @classmethod
    def get_task_priorities_download(cls) -> list[dict[str, int | str | float]]:
        """Get the task priorities for download."""
        task_priorities = cls._get_task_priorities()[0]
        return [
            {
                "Paper Number": paper_number,
                "Question Index": question_idx,
                "Priority Value": priority,
                "Status": status,
            }
            for (
                (paper_number, question_idx),
                (priority, status),
            ) in task_priorities.items()
        ]

    @staticmethod
    def handle_file_upload(csv_data: DictReader) -> dict[tuple[int, int], int | float]:
        """Handle uploaded file data of task priorities.

        Args:
            csv_data: The CSV data parsed with DictReader and caller must have
            validated that each row contains the keys: ["Paper Number", "Question Index", "Priority Value"].

        Returns:
            A dictionary of task priorities, keyed by
            (paper_number, question_index) pairs.
        """
        custom_priorities = {}
        for row in csv_data:
            key = (int(row["Paper Number"]), int(row["Question Index"]))
            custom_priorities[key] = int(row["Priority Value"])

        return custom_priorities
