# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Julian Lapenna

import arrow
import statistics

from Mark.models import MarkingTask, Annotation


class TaMarkingService:
    """Service for the TA marking information."""

    def get_all_ta_annotations(self):
        """Return all annotations."""
        return Annotation.objects.all()

    def get_annotations_from_user(self, user):
        """Return all annotations from a user.

        Args:
            user: (User) The user to get the annotations from.
        """
        return Annotation.objects.filter(user=user)

    def get_annotations_from_user_and_paper(self, user, paper):
        """Return all annotations from a user.

        Args:
            user: (User) The user to get the annotations from.
            paper: (Paper) The paper to get the annotations from.
        """
        return Annotation.objects.filter(user=user, task__paper=paper)

    def get_csv_header(self) -> list:
        """Get the header for the csv file.

        Returns:
            list: The header for the csv file. Contains TA marking information,
            paper, question and version info, timestamps and warnings.
        """
        keys = [
            "user",
            "paper_number",
            "question_number",
            "question_version",
            "score_given",
            "max_score",
            "minutes_spent_marking",
            "last_update_time",
            "csv_write_time",
            "warnings",
        ]

        return keys

    def build_csv_data(self) -> list:
        """Get the info for all students in a list for building a csv file to download.

        Returns:
            list: each element is a dictionary containing the marking information for an annotation.
        """
        annotations = Annotation.objects.all()
        csv_data = []
        for annotation in annotations:
            csv_data.append(self.get_annotation_info_download(annotation))

        return csv_data

    def get_annotation_info_download(self, annotation: Annotation) -> dict:
        """Get the marking information for an annotation.

        Args:
            annotation: (Annotation) The annotation to get the marking information from.

        Returns:
            dict: keyed by string information about the annotation (i.e. "score": 2, "question_number" : 3).
        """
        annotation_info = {
            "user": annotation.user.username,
            "paper_number": annotation.task.paper.paper_number,
            "question_number": annotation.task.question_number,
            "question_version": annotation.task.question_version,
            "score_given": annotation.score,
            "max_score": annotation.annotation_data["maxMark"],
            "minutes_spent_marking": annotation.marking_time,
            "last_update_time": arrow.get(annotation.time_of_last_update).isoformat(
                " ", "seconds"
            ),
            "csv_write_time": arrow.now().isoformat(" ", "seconds"),
        }
        return annotation_info

    def get_time_spent_on_question(
        self, question: int, q_version: int = 0, average: bool = False
    ) -> float:
        """Get the time spent on a question by all markers.

        By default, returns the total time spent but if average == True, returns the average
        time spent instead.

        Args:
            question: (int) The question number to get the total time spent on.
            q_version: (int) The version of the question to get the total time spent on.
                Defaults to 0 which ignores version, otherwise the version is used.
            average: (bool) Whether to get the average time spent on a question by all markers.

        Returns:
            The time (total or average) spent on a question by all markers in minutes.
        """
        total_time = 0.0
        marking_tasks = MarkingTask.objects.filter(question_number=question)
        if q_version != 0:
            marking_tasks = marking_tasks.filter(question_version=q_version)

        for marking_task in marking_tasks:
            if marking_task.latest_annotation:
                total_time += marking_task.latest_annotation.marking_time

        if average:
            return round(total_time / marking_tasks.count(), 1)

        return total_time

    def get_std_time_spent_on_question(
        self, question: int, q_version: int = 0
    ) -> float:
        """Get the std of time spent on a question by all markers.

        Args:
            question: (int) The question number to get the total time spent on.
            q_version: (int) The version of the question to get the total time spent on.
                Defaults to 0 which ignores version, otherwise the version is used.

        Returns:
            The std time spent on a question by all markers in minutes.
        """
        times = []
        marking_tasks = MarkingTask.objects.filter(question_number=question)
        if q_version != 0:
            marking_tasks = marking_tasks.filter(question_version=q_version)

        for marking_task in marking_tasks:
            if marking_task.latest_annotation:
                times.append(marking_task.latest_annotation.marking_time)

        if len(times) == 0:
            return 0.0

        return round(statistics.stdev(times), 1)