# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Andrew Rechnitzer

from django.contrib.auth.models import User

from Identify.services import IdentifyTaskService
from Papers.models import Paper


class IDHomeworkService:
    """Functions for Identify homework uploads."""

    def identify_homework(
        self, user_obj: User, paper_number: int, student_id: str, student_name: str
    ):
        try:
            paper_obj = Paper.objects.get(paper_number=paper_number)
        except Paper.DoesNotExist:
            raise ValueError(f"Cannot find paper with number {paper_number}")

        its = IdentifyTaskService()
        # set any previous id-ing as out of date and create a new task
        its.create_task(paper_obj)
        # then claim it for the user and id it with the provided data
        its.claim_task(user_obj, paper_number)
        its.identify_paper(user_obj, paper_number, student_id, student_name)

    def identify_homework_cmd(
        self, username: str, paper_number: int, student_id: str, student_name: str
    ):
        try:
            user_obj = User.objects.get(
                username__iexact=username, groups__name="manager"
            )
        except User.DoesNotExist as e:
            raise ValueError(
                f"User '{username}' does not exist or has wrong permissions."
            ) from e

        self.identify_homework(user_obj, paper_number, student_id, student_name)
