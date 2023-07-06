# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Julian Lapenna

import arrow

from Mark.models import MarkingTask, Annotation
from Papers.models.paper_structure import Paper
from Identify.models import PaperIDAction, PaperIDTask


class StudentMarkService:
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

    def get_n_of_question_marked(self, question_num: int) -> int:
        """Get the count of how many papers have marked a question.

        Args:
            question_num: The question number.

        Returns:
            The count of how many papers a mark for this question.
        """
        return MarkingTask.objects.filter(
            question_number=question_num, latest_annotation__isnull=False
        ).count()

    def get_student_info_from_paper(
        self, paper_num: int, original: bool = False
    ) -> dict:
        """Get student info from a paper number.

        Args:
            paper_num: The paper number.
            original: Gets the first edition of a mark if true, otherwise get latest (default).

        Returns:
            dict: keyed by string information about the student (i.e. "student_id": 1234, "q1_version" : 2).
        """
        paper_obj = Paper.objects.get(pk=paper_num)
        marking_tasks = paper_obj.markingtask_set.all()
        paper_id_task = PaperIDTask.objects.filter(paper=paper_obj).first()

        student_info = {"paper_number": paper_num}

        # student info
        if paper_id_task:
            paper_id_action = PaperIDAction.objects.filter(task=paper_id_task).first()
            if paper_id_action:
                student_info.update(
                    {
                        "student_id": paper_id_action.student_id,
                        "student_name": paper_id_action.student_name,
                    }
                )

        # mark info
        total = 0
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
                student_info.update(
                    {
                        "q"
                        + str(marking_task.question_number)
                        + "_mark": current_annotation.score,
                        "q"
                        + str(marking_task.question_number)
                        + "_version": marking_task.question_version,
                    }
                )
                total += current_annotation.score

        student_info.update(
            {
                "total_mark": total,
                "csv_write_time": arrow.utcnow().isoformat(" ", "seconds"),
            }
        )

        return student_info

    def get_all_students_download(self, original: bool = False) -> list:
        """Get the info for all students in a list for building a csv file to download.

        Args:
            original: Gets the first edition of a mark if true, otherwise get latest (default).

        Returns:
            list: each element is a dictionary containing the information about an individual student.
        """
        papers = Paper.objects.all()
        csv_data = []
        for paper in papers:
            csv_data.append(
                self.get_student_info_from_paper(paper.paper_number, original)
            )

        return csv_data

    def get_csv_header(self, spec) -> list:
        """Get the header for the csv file.

        Args:
            spec: The specification for the paper.

        Returns:
            list: The header for the csv file. Contains student info, marks,
            version info, timestamps and warnings.
        """
        keys = ["student_id", "student_name", "paper_number"]
        for q in range(1, spec["numberOfQuestions"] + 1):
            keys.append("q" + str(q) + "_mark")
        keys.append("total_mark")
        for q in range(1, spec["numberOfQuestions"] + 1):
            keys.append("q" + str(q) + "_version")
        keys.extend(["last_update", "csv_write_time", "warnings"])

        return keys
