# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Julian Lapenna

from Mark.models import Annotation
from Mark.models.tasks import MarkingTask
from Papers.models.paper_structure import Paper


class StudentMarksService:
    """Service for the Student Marks page."""

    def get_marks_from_paper(self, paper_num : int) -> dict:
        """Get the marks for a paper.

        Args:
            paper_num: The paper number.

        Returns:
            The mark information for each question in the paper.
        """
        paper_obj = Paper.objects.get(pk=paper_num)
        marking_tasks = paper_obj.markingtask_set.all()
        annotations = Annotation.objects.filter(task__in=marking_tasks).order_by("edition")

        annotations_by_task = {}
        for annotation in annotations:
            annotations_by_task[annotation.task] = annotation
        
        print(annotations)
        print(annotations_by_task)

        questions = {}
        for marking_task in marking_tasks:
            annotation_data = annotations_by_task[marking_task].annotation_data
            # questions[marking_task.question_number] = {
            questions["q" + str(marking_task.question_number)] = {
                "question": marking_task.question_number,
                "version": marking_task.question_version,
                "out_of": annotation_data["maxMark"],
                "student_mark": annotations_by_task[marking_task].score,
            }

        # return { paper_num: questions }
        return { "p" + str(paper_num): questions }
