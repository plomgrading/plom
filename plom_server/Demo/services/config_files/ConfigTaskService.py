# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Edith Coates

"""Handle creating task-related server state from a config file.

Assumes that the config describes a valid server state, and that
the functions in ConfigPreparationService have already been called.
"""

from Preparation.services import TestPreparedSetting
from Papers.models import Paper
from Papers.services import SpecificationService
from Mark.services import MarkingTaskService
from Identify.services import IdentifyTaskService

from . import PlomServerConfig


def init_all_marking_tasks():
    """Create marking tasks from a config."""
    n_questions = SpecificationService.get_n_questions()
    all_papers = Paper.objects.all()
    mts = MarkingTaskService()
    for paper in all_papers:
        for i in range(n_questions):
            question_number = i + 1
            mts.create_task(
                paper=paper,
                question_number=question_number,
            )


def init_all_id_tasks():
    """Create ID'ing tasks from a config."""
    its = IdentifyTaskService()
    for paper in Paper.objects.all():
        its.create_task(paper)


def init_all_tasks(config: PlomServerConfig):
    if config.auto_init_tasks and TestPreparedSetting.is_test_prepared:
        init_all_marking_tasks()
        init_all_id_tasks()
