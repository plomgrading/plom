# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Julian Lapenna

from Mark.models import Annotation
from Mark.models.tasks import MarkingTask
from Papers.models.paper_structure import Paper


class StudentMarksService:
    """Service for the Student Marks page."""

    def get_marks_from_paper(self, paper_num: int, original: bool = False) -> dict:
        """Get the marks for a paper.

        Args:
            paper_num: The paper number.
            original: Gets the first edition of a mark if true, otherwise get latest (default).

        Returns:
            The mark information for each question in the paper.
        """
        paper_obj = Paper.objects.get(pk=paper_num)
        marking_tasks = paper_obj.markingtask_set.all()

        questions = {}
        for marking_task in marking_tasks.order_by("question_number"):
            if original:
                current_annotation = marking_task.annotation_set.order_by(
                    "edition"
                ).first()
            else:
                current_annotation = marking_task.annotation_set.order_by(
                    "-edition"
                ).first()

            if current_annotation:
                questions[marking_task.question_number] = {
                    "question": marking_task.question_number,
                    "version": marking_task.question_version,
                    "out_of": current_annotation.annotation_data["maxMark"],
                    "student_mark": current_annotation.score,
                }

        return {paper_num: questions}

    def get_all_marks(self, original: bool = False) -> dict:
        """Get the marks for all papers.

        Args:
            original: Gets the first edition of a mark if true, otherwise get latest (default).

        Returns:
            The mark information for each question in each paper.
        """
        papers = Paper.objects.all()
        print("PAPERS: ", papers)
        marks = {}
        for paper in papers:
            marks.update(self.get_marks_from_paper(paper.paper_number, original))

        return marks

    def get_all_papers(self):
        """Get all papers.

        Returns:
            Queryset: All paper objects.
        """
        return Paper.objects.all()

    def get_marks_from_paper_set(self, paper_set: set, original: bool = False) -> dict:
        """Get the marks for a set of papers.

        Args:
            paper_set: The set of (int) paper numbers.
            original: Gets the first edition of a mark if true, otherwise get latest (default).

        Returns:
            The mark information for each question in each paper.
        """
        marks = {}
        for paper_num in paper_set:
            marks.update(self.get_marks_from_paper(paper_num, original))

        return marks
