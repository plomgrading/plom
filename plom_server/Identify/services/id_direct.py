# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2024-2026 Colin B. Macdonald

from django.contrib.auth.models import User
from django.db import transaction

from plom_server.Papers.models import Paper
from ..services import IdentifyTaskService


class IDDirectService:
    """Functions for Identify (directly) uploads - typically for homework."""

    @staticmethod
    def identify_direct(
        user_obj: User, paper_number: int, student_id: str, student_name: str
    ):
        """Identify directly a given paper with as the student id and name.

        "Direct" here refers to bypassing the "Task" system that is usually invoked
        by the desktop Plom Client, for example.

        If there are already any existing IDTasks for this paper, they will
        be set to out-of-date.

        Args:
            user_obj: The user doing the identifying
            paper_number: which paper to id
            student_id: the student's id
            student_name: the student's name

        Raises:
            ValueError: no such paper
            RuntimeError: paper already claimed, or paper already ID'd.
                which should not be possible but... ya know...
            IntegrityError: student_id is in-use elsewhere.
        """
        try:
            paper_obj = Paper.objects.get(paper_number=paper_number)
        except Paper.DoesNotExist:
            raise ValueError(f"Cannot find paper with number {paper_number}")

        with transaction.atomic():
            # set any previous id-ing as out of date and create a new task
            IdentifyTaskService.create_task(paper_obj)
            # then claim it for the user and id it with the provided data
            # (b/c we have the atomic transaction, I believe no one else can
            # claim the task we just created, so this "cannot" fail.  If it
            # does we'll get a RuntimeError).
            IdentifyTaskService.claim_task(user_obj, paper_number)
            IdentifyTaskService.identify_paper(
                user_obj, paper_number, student_id, student_name
            )

    @classmethod
    def identify_direct_cmd(
        cls, username: str, paper_number: int, student_id: str, student_name: str
    ):
        """This function backs the command-line utility."""
        try:
            # TODO: the other Views check for manager OR lead_marker
            user_obj = User.objects.get(
                username__iexact=username, groups__name="manager"
            )
        except User.DoesNotExist as e:
            raise ValueError(
                f"User '{username}' does not exist or has wrong permissions."
            ) from e

        cls.identify_direct(user_obj, paper_number, student_id, student_name)
