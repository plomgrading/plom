# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Julian Lapenna

from Mark.models import MarkingTask, Annotation
from Papers.models.paper_structure import Paper


class StudentMarksService:
    """Service for the Student Marks page."""

    def get_marks_from_paper(self, paper_num: int, original: bool = False) -> dict:
        """Get the marks for a paper.

        Args:
            paper_num: The paper number.
            original: Gets the first edition of a mark if true, otherwise get latest (default).

        Returns:
            dict: keyed by paper number whose values are a dictionary holding 
            the mark information for each question in the paper.
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

    def get_n_of_question_marked(self, question_num: int) -> float:
        """Get the percentage of a question that has been marked.

        Args:
            question_num: The question number.

        Returns:
            The percentage of the question that has been marked.
        """
        marking_tasks = MarkingTask.objects.filter(question_number=question_num)

        return Annotation.objects.filter(task__in=marking_tasks).count()  # TODO: .filter(newest_version=True) once implemented

    def get_marks_from_paper_download(self, paper_num: int, original: bool = False) -> dict:
        """Get the marks for a paper.

        Args:
            paper_num: The paper number.
            original: Gets the first edition of a mark if true, otherwise get latest (default).

        Returns:
            dict: keyed by string information about the paper (i.e. "Q1_version" : 2).
        """
        paper_obj = Paper.objects.get(pk=paper_num)
        marking_tasks = paper_obj.markingtask_set.all()

        marks = {"paper": paper_num}
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
                marks.update(
                    {
                        "Q" + str(marking_task.question_number) + "_mark" : current_annotation.score,
                        "Q" + str(marking_task.question_number) + "_version" : marking_task.question_version,
                    }
                )

        return marks

    def get_all_marks_download(self, original: bool = False) -> list:
        """Get the marks for all papers.

        Args:
            original: Gets the first edition of a mark if true, otherwise get latest (default).

        Returns:
            list: each element is a dictionary containing the information about an individual paper.
        """
        papers = Paper.objects.all()
        marks = []
        for paper in papers:
            marks.append(self.get_marks_from_paper_download(paper.paper_number, original))

        return marks
