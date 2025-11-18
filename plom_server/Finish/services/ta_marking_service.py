# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Julian Lapenna
# Copyright (C) 2023-2024 Andrew Rechnitzer
# Copyright (C) 2024-2025 Colin B. Macdonald

import csv
import datetime as dt
from io import StringIO

import arrow

from django.db.models import Sum, Avg, StdDev
from django.utils import timezone

from ..services import StudentMarkService
from plom_server.Mark.models import MarkingTask
from plom_server.Mark.services import MarkingTaskService


class TaMarkingService:
    """Service for the TA marking information."""

    def get_csv_header(self) -> list:
        """Get the header for the csv file.

        Returns:
            List holding the header for the csv file. Contains TA marking information,
            paper, question and version info, timestamps and warnings.
        """
        keys = [
            "user",
            "paper_number",
            "question_index",
            "question_version",
            "score_given",
            "max_score",
            "seconds_spent_marking",
            "last_update_time",
        ]

        return keys

    def build_csv_data(self) -> list:
        """Get information about the latest annotation for all marking tasks that are complete.

        Returns:
            List where each element is a dict keyed by str, representing a single annotation.

        Raises:
            None expected
        """
        complete_marking_tasks = (
            MarkingTaskService()
            .get_complete_marking_tasks()
            .prefetch_related("paper", "latest_annotation", "latest_annotation__user")
            .order_by(
                "latest_annotation__user__username",
                "paper__paper_number",
                "question_index",
            )
        )
        csv_data = []
        for task in complete_marking_tasks:
            assert task.latest_annotation.user is not None
            assert task.latest_annotation.annotation_data is not None
            csv_data.append(
                {
                    "user": task.latest_annotation.user.username,
                    "paper_number": task.paper.paper_number,
                    "question_index": task.question_index,
                    "question_version": task.question_version,
                    "score_given": task.latest_annotation.score,
                    "max_score": task.latest_annotation.annotation_data["maxMark"],
                    "seconds_spent_marking": task.latest_annotation.marking_time,
                    "last_update_time": arrow.get(task.last_update).isoformat(
                        " ", "seconds"
                    ),
                }
            )

        return csv_data

    def build_ta_info_csv_as_string(self) -> str:
        """Constructs TA info csv and casts it to a string."""
        ta_info = self.build_csv_data()
        keys = self.get_csv_header()
        csv_io = StringIO()
        w = csv.DictWriter(csv_io, keys, extrasaction="ignore")
        w.writeheader()
        w.writerows(ta_info)
        csv_io.seek(0)

        return csv_io.getvalue()

    def get_total_time_spent_on_question(
        self, qidx: int, *, version: int = 0
    ) -> float | None:
        """Get the total time spent on a question by all markers.

        Args:
            qidx: The question index to get the total time spent on.

        Keyword Args:
            version: The version of the question to get the total time spent on.
                Defaults to 0 which ignores version, otherwise the version is used.

        Returns:
            None if there are no annotations for the question otherwise, the total time
            spent on a question by all markers in seconds as a float.

        Raises:
            None expected
        """
        service = MarkingTaskService()
        return service.get_tasks_from_question_with_annotation(qidx, version).aggregate(
            Sum("latest_annotation__marking_time")
        )["latest_annotation__marking_time__sum"]

    def get_average_time_spent_on_question(
        self, qidx: int, *, version: int = 0
    ) -> float | None:
        """Get the average time spent on a question by all markers.

        Args:
            qidx: The question index to get the average time spent on.

        Keyword Args:
            version: The version of the question to get the average time spent on.
                Defaults to 0 which ignores version, otherwise the version is used.

        Returns:
            None if there are no annotations for the question otherwise, the average time
            spent on a question by all markers in seconds as a float.

        Raises:
            None expected
        """
        service = MarkingTaskService()
        return service.get_tasks_from_question_with_annotation(qidx, version).aggregate(
            Avg("latest_annotation__marking_time")
        )["latest_annotation__marking_time__avg"]

    def get_stdev_time_spent_on_question(
        self, qidx: int, *, version: int = 0
    ) -> float | None:
        """Get the standard deviation of time spent on a question by all markers.

        Args:
            qidx: The question index to get the standard deviation time spent on.

        Keyword Args:
            version: The version of the question to get the standard deviation time
                spent on.  Defaults to 0 which ignores version, otherwise
                the version is used.

        Returns:
            None if there are no annotations for the question otherwise,
            the standard deviation time spent on a question by all markers
            in seconds as a float.

        Raises:
            None expected
        """
        service = MarkingTaskService()
        return service.get_tasks_from_question_with_annotation(qidx, version).aggregate(
            StdDev("latest_annotation__marking_time")
        )["latest_annotation__marking_time__stddev"]

    def all_marking_times_for_web(self, n_questions: int) -> tuple:
        """Get the total, average and standard deviation of time spent on each question.

        Args:
            n_questions: The number of questions in the paper.

        Returns:
            Tuple holding 3 lists that contain the total, average and standard deviation
            times respectively for marking each question held in a humanized format.

        Raises:
            None expected
        """
        service = TaMarkingService()
        present = arrow.utcnow()

        total_seconds = [
            service.get_total_time_spent_on_question(q)
            for q in range(1, n_questions + 1)
        ]
        average_seconds = [
            service.get_average_time_spent_on_question(q)
            for q in range(1, n_questions + 1)
        ]
        std_seconds = [
            service.get_stdev_time_spent_on_question(q)
            for q in range(1, n_questions + 1)
        ]

        total_times_spent: list[str | None] = [None] * n_questions
        average_times_spent: list[str | None] = [None] * n_questions
        std_times_spent: list[str | None] = [None] * n_questions

        for i, s in enumerate(total_seconds):
            if s:
                total_times_spent[i] = present.shift(seconds=s).humanize(
                    present, only_distance=True, granularity=["hour", "minute"]
                )
        for i, s in enumerate(average_seconds):
            if s:
                average_times_spent[i] = present.shift(seconds=s).humanize(
                    present, only_distance=True, granularity=["minute", "second"]
                )
        for i, s in enumerate(std_seconds):
            if s:
                std_times_spent[i] = present.shift(seconds=s).humanize(
                    present, only_distance=True, granularity=["minute", "second"]
                )

        return total_times_spent, average_times_spent, std_times_spent

    def get_avg_n_of_questions_marked_per_day(self, question_idx: int) -> float:
        """Get the average number of questions marked per day for a given question.

        Args:
            question_idx: Which question to get the average number of questions
                marked per day for.  1-based question index.

        Returns:
            The average number of questions marked per day for a given question as a float.

        Raises:
            None expected
        """
        num_questions_marked = StudentMarkService.get_n_of_question_marked(question_idx)

        marking_task = (
            MarkingTask.objects.filter(question_index=question_idx)
            .order_by("time")
            .first()
        )

        if not marking_task:  # No marking tasks in the database
            return 0.0

        num_days = max(
            self.round_days(timezone.now() - marking_task.time),
            1,
        )  # Ensure at least 1 day is returned to prevent division by 0

        return num_questions_marked / num_days

    def get_estimate_days_remaining(self, question_idx: int) -> float | None:
        """Get the estimated number of days remaining to mark a given question.

        Args:
            question_idx: Which question to get the estimated number of days remaining
                to mark.  1-based question index.

        Returns:
            None if no questions have been marked yet otherwise, the estimated number of days
            remaining to mark a given question .

        Raises:
            None expected
        """
        num_questions_remaining = (
            MarkingTask.objects.filter(question_index=question_idx)
            .exclude(status=MarkingTask.COMPLETE)
            .count()
        )

        avg_per_day = self.get_avg_n_of_questions_marked_per_day(question_idx)
        assert avg_per_day >= 0
        if avg_per_day == 0:
            return None

        return round(num_questions_remaining / avg_per_day, 2)

    def get_estimate_hours_remaining(self, question_idx: int) -> float | None:
        """Get the estimated number of hours remaining to mark a given question.

        Args:
            question_idx: Which question to get the estimated number of
                hours remaining to mark.  1-based question index.

        Returns:
            None if no questions have been marked yet otherwise, the estimated number of hours
            remaining to mark a given question.

        Raises:
            None expected
        """
        avg_time_on_question = self.get_average_time_spent_on_question(question_idx)
        num_questions_remaining = (
            MarkingTask.objects.filter(question_index=question_idx)
            .exclude(status=MarkingTask.COMPLETE)
            .count()
        )
        if not avg_time_on_question:
            return None

        return round(num_questions_remaining * avg_time_on_question / 3600, 2)

    def round_days(self, obj: dt.timedelta) -> int:
        """Round a timedelta object to the nearest day.

        Args:
            obj: The timedelta object to round.

        Returns:
            The integer days of the timedelta object rounded to the nearest day.
        """
        return round(obj.total_seconds() / 86400)
