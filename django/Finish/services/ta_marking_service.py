# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Julian Lapenna

import arrow
import datetime as dt

from django.db.models import Sum, Avg, StdDev
from django.utils import timezone

from Finish.services import StudentMarkService
from Mark.models import MarkingTask, Annotation
from Mark.services import MarkingTaskService


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
            "seconds_spent_marking",
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
            "seconds_spent_marking": annotation.marking_time,
            "last_update_time": arrow.get(annotation.time_of_last_update).isoformat(
                " ", "seconds"
            ),
            "csv_write_time": arrow.now().isoformat(" ", "seconds"),
        }
        return annotation_info

    def get_total_time_spent_on_question(
        self, question: int, *, version: int = 0
    ) -> float:
        """Get the total time spent on a question by all markers.

        Args:
            question: (int) The question number to get the total time spent on.

        Keyword Args:
            version: (int) The version of the question to get the total time spent on.
                Defaults to 0 which ignores version, otherwise the version is used.

        Returns:
            The total time spent on a question by all markers in seconds.
        """
        service = MarkingTaskService()
        return service.get_tasks_from_question_with_annotation(
            question=question, version=version
        ).aggregate(Sum("latest_annotation__marking_time"))[
            "latest_annotation__marking_time__sum"
        ]

    def get_average_time_spent_on_question(
        self, question: int, *, version: int = 0
    ) -> float | None:
        """Get the average time spent on a question by all markers.

        Args:
            question: (int) The question number to get the average time spent on.

        Keyword Args:
            version: (int) The version of the question to get the average time spent on.
                Defaults to 0 which ignores version, otherwise the version is used.

        Returns:
            None: If there are no annotations for the question.
            Float: The average time spent on a question by all markers in seconds.
        """
        service = MarkingTaskService()
        return service.get_tasks_from_question_with_annotation(
            question=question, version=version
        ).aggregate(Avg("latest_annotation__marking_time"))[
            "latest_annotation__marking_time__avg"
        ]

    def get_stdev_time_spent_on_question(
        self, question: int, *, version: int = 0
    ) -> float:
        """Get the standard deviation of time spent on a question by all markers.

        Args:
            question: (int) The question number to get the standard deviation time spent on.

        Keyword Args:
            version: (int) The version of the question to get the standard deviation time spent on.
                Defaults to 0 which ignores version, otherwise the version is used.

        Returns:
            The standard deviation time spent on a question by all markers in seconds.
        """
        service = MarkingTaskService()
        return service.get_tasks_from_question_with_annotation(
            question=question, version=version
        ).aggregate(StdDev("latest_annotation__marking_time"))[
            "latest_annotation__marking_time__stddev"
        ]

    def all_marking_times_for_web(self, n_questions: int) -> tuple:
        """Get the total, average and standard deviation of time spent on each question.

        Args:
            n_questions: (int) The number of questions in the paper.

        Returns:
            tuple: 3 lists that contain the total, average and standard deviation times respectively
                for marking each question held in a humanized format.
        """
        service = TaMarkingService()
        present = arrow.utcnow()

        total_seconds = [
            service.get_total_time_spent_on_question(question=q)
            for q in range(1, n_questions + 1)
        ]
        average_seconds = [
            service.get_average_time_spent_on_question(question=q)
            for q in range(1, n_questions + 1)
        ]
        std_seconds = [
            service.get_stdev_time_spent_on_question(question=q)
            for q in range(1, n_questions + 1)
        ]

        total_times_spent = [None] * n_questions
        average_times_spent = [None] * n_questions
        std_times_spent = [None] * n_questions

        if not None in total_seconds:
            total_times_spent = [
                present.shift(
                    seconds=s
                ).humanize(present, only_distance=True, granularity=["hour", "minute"])
                for s in total_seconds
            ]
        if not None in average_seconds:
            average_times_spent = [
                present.shift(
                    seconds=s
                ).humanize(
                    present, only_distance=True, granularity=["minute", "second"]
                )
                for s in average_seconds
            ]
        if not None in std_seconds:
            std_times_spent = [
                present.shift(
                    seconds=s
                ).humanize(
                    present, only_distance=True, granularity=["minute", "second"]
                )
                for s in std_seconds
            ]

        return total_times_spent, average_times_spent, std_times_spent

    def get_avg_n_of_questions_marked_per_day(self, question: int) -> float:
        """Get the average number of questions marked per day for a given question.

        Args:
            question: (int) The question number to get the average number of questions marked per day for.

        Returns:
            float: The average number of questions marked per day for a given question.
            None: if less than 12 hours have passed since the first question was marked.
        """
        service = StudentMarkService()
        num_questions_marked = service.get_n_of_question_marked(question)

        num_days = max(self.round_days(
            timezone.now()
            - MarkingTask.objects.filter(question_number=question)
            .order_by("time")
            .first()
            .time
        ), 1)  # Ensure at least 1 day is returned to prevent division by 0

        return num_questions_marked / num_days

    def get_estimate_days_remaining(self, question: int) -> float | None:
        """Get the estimated number of days remaining to mark a given question.

        Args:
            question: (int) The question number to get the estimated number of days remaining to mark.

        Returns:
            None: if no questions have been marked yet; otherwise,
            float: The estimated number of days remaining to mark a given question.
        """
        num_questions_remaining = MarkingTask.objects.filter(
            question_number=question, latest_annotation__isnull=True
        ).count()

        avg_per_day = self.get_avg_n_of_questions_marked_per_day(question=question)
        if avg_per_day == 0:
            return None

        return num_questions_remaining / avg_per_day

    def get_estimate_hours_remaining(self, question: int) -> float:
        """Get the estimated number of hours remaining to mark a given question.

        Args:
            question: (int) The question number to get the estimated number of hours remaining to mark.

        Returns:
            float: The estimated number of hours remaining to mark a given question.
        """
        avg_time_on_question = self.get_average_time_spent_on_question(
            question=question
        )
        num_questions_remaining = MarkingTask.objects.filter(
            question_number=question, latest_annotation__isnull=True
        ).count()
        if not avg_time_on_question:
            return None

        return num_questions_remaining * avg_time_on_question / 3600

    def round_days(self, obj: dt.timedelta) -> int:
        """Round a timedelta object to the nearest day.

        Args:
            obj: (dt.timedelta) The timedelta object to round.

        Returns:
            int: The timedelta object rounded to the nearest day.
        """
        return round(obj.total_seconds() / 86400)
