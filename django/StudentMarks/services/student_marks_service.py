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
        if original:
            annotations = Annotation.objects.filter(task__in=marking_tasks).order_by(
                "-edition"
            )
        else:
            annotations = Annotation.objects.filter(task__in=marking_tasks).order_by(
                "edition"
            )

        annotations_by_task = {}
        for annotation in annotations:
            annotations_by_task[annotation.task] = annotation

        questions = {}
        for marking_task in marking_tasks.order_by("question_number"):
            annotation_data = annotations_by_task[marking_task].annotation_data
            # questions["q" + str(marking_task.question_number)] = {
            questions[marking_task.question_number] = {
                "question": marking_task.question_number,
                "version": marking_task.question_version,
                "out_of": annotation_data["maxMark"],
                "student_mark": annotations_by_task[marking_task].score,
            }

        return {paper_num: questions}
        # return { "p" + str(paper_num): questions }

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
