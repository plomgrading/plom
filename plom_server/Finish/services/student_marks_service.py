# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Julian Lapenna
# Copyright (C) 2023 Colin B. Macdonald
# Copyright (C) 2023 Divy Patel
# Copyright (C) 2023-2024 Andrew Rechnitzer

# Yuck, replace this below when we drop Python 3.8 support
from typing import Dict, Union

from Mark.services import MarkingTaskService
from Mark.models import MarkingTask
from Papers.models.paper_structure import Paper
from .reassemble_service import ReassembleService


class StudentMarkService:
    """Service for the Student Marks page."""

    def get_marks_from_paper(self, paper_num: int) -> dict:
        """Get the marks for a paper.

        Args:
            paper_num: The paper number.

        Returns:
            Dict keyed by paper number whose values are a dictionary holding
            the mark information for each question in the paper.
        """
        try:
            paper_obj = Paper.objects.get(pk=paper_num)
        except Paper.DoesNotExist:
            return {}
        marking_tasks = (
            paper_obj.markingtask_set.all()
            .select_related("latest_annotation")
            .exclude(status=MarkingTask.OUT_OF_DATE)
        )
        questions: Dict[int, Union[Dict, str]] = {}
        for marking_task in marking_tasks.order_by("question_number"):
            current_annotation = marking_task.latest_annotation
            if current_annotation:
                questions[marking_task.question_number] = {
                    "question": marking_task.question_number,
                    "version": marking_task.question_version,
                    "out_of": current_annotation.annotation_data["maxMark"],
                    "student_mark": current_annotation.score,
                }
            else:
                # String value so that it questions.get(i) doesn't return None
                questions[marking_task.question_number] = "Not marked"

        return {paper_num: questions}

    def get_all_marks(self) -> dict:
        """Get the marks for all papers.

        Returns:
            Dict containing the mark information for each question in each paper. Keyed by
            paper number whose values are a dictionary holding the mark information for each
            question in the paper.
        """
        paper_nums = MarkingTask.objects.values_list(
            "paper__paper_number", flat=True
        ).distinct()
        marks = {}
        for paper_num in paper_nums:
            marks.update(self.get_marks_from_paper(paper_num))
        # Sort by paper number
        return {k: marks[k] for k in sorted(marks)}

    def get_marks_from_paper_set(self, paper_set: set) -> dict:
        """Get the marks for a set of papers.

        Args:
            paper_set: The set of (int) paper numbers.

        Returns:
            Dict containing the mark information for each question in each paper. Keyed by paper number whose
            values are a dictionary holding the mark information for each question in the paper.
        """
        marks = {}
        for paper_num in paper_set:
            marks.update(self.get_marks_from_paper(paper_num))

        return marks

    def get_n_of_question_marked(self, question: int, *, version: int = 0) -> int:
        """Get the count of how many papers have marked a specific question.

        Args:
            question: The question number.

        Keyword Args:
            version: The version of the question.

        Returns:
            The count of how many papers a mark for this question.

        Raises:
            None expected
        """
        service = MarkingTaskService()
        return service.get_tasks_from_question_with_annotation(
            question=question, version=version
        ).count()

    def get_student_info_from_paper(
        self,
        paper_num: int,
    ) -> dict:
        """Get student info from a paper number.

        Args:
            paper_num: The paper number.

        Returns:
            Dict keyed by string information about the student (i.e. "student_id": 1234, "q1_version" : 2).

        Raises:
            Paper.DoesNotExist: If the paper does not exist in the database.
        """
        try:
            paper_obj = Paper.objects.get(pk=paper_num)
        except Paper.DoesNotExist:
            raise Paper.DoesNotExist

        # TODO - this spreadsheet stuff in reassemble service should move to student mark service
        return ReassembleService().paper_spreadsheet_dict(paper_obj)

    def get_all_students_download(
        self,
        version_info: bool,
        timing_info: bool,
        warning_info: bool,
    ) -> list:
        """Get the info for all students in a list for building a csv file to download.

        Args:
            version_info: Whether to include the version info.
            timing_info: Whether to include the timing info.
            warning_info: Whether to include the warning info.

        Returns:
            List where each element is a dictionary containing the information about an individual student.

        Raises:
            None expected
        """
        paper_nums = sorted(
            MarkingTask.objects.values_list("paper__paper_number", flat=True).distinct()
        )
        csv_data = []
        for paper_num in paper_nums:
            csv_data.append(self.get_student_info_from_paper(paper_num))

        return csv_data

    def get_csv_header(
        self, spec: Dict, version_info: bool, timing_info: bool, warning_info: bool
    ) -> list:
        """Get the header for the csv file.

        Args:
            spec: The specification for the paper.
            version_info: Whether to include the version info.
            timing_info: Whether to include the timing info.
            warning_info: Whether to include the warning info.

        Returns:
            List holding the header for the csv file. Contains student info, marks,
            version info, timestamps and warnings.

        Raises:
            None expected
        """
        keys = ["student_id", "student_name", "paper_number", "total_mark"]
        numberOfQuestions = spec["numberOfQuestions"]
        for q in range(1, numberOfQuestions + 1):
            keys.append(f"q{q}_mark")
        if version_info:
            for q in range(1, numberOfQuestions + 1):
                keys.append(f"q{q}_version")
        if timing_info:
            keys.extend(["last_update"])
        if warning_info:
            keys.append("warnings")

        return keys
