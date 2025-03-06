# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Edith Coates
# Copyright (C) 2024 Andrew Rechnitzer
# Copyright (C) 2024 Colin B. Macdonald

"""Handle creating task-related server state from a config file.

Assumes that the config describes a valid server state, and that
the functions in ConfigPreparationService have already been called.
"""

from plom_server.Preparation.services import PapersPrinted
from plom_server.Papers.models import Paper
from plom_server.Papers.services import SpecificationService
from plom_server.Mark.services import MarkingTaskService
from plom_server.Identify.services import IdentifyTaskService

from . import PlomServerConfig


def init_all_marking_tasks():
    """Create marking tasks from a config."""
    all_papers = Paper.objects.all()
    mts = MarkingTaskService()
    for paper in all_papers:
        for qidx in SpecificationService.get_question_indices():
            mts.create_task(paper=paper, question_index=qidx)


def init_all_id_tasks():
    """Create ID'ing tasks from a config."""
    its = IdentifyTaskService()
    for paper in Paper.objects.all():
        its.create_task(paper)


def init_all_tasks(config: PlomServerConfig):
    if config.auto_init_tasks and PapersPrinted.have_papers_been_printed():
        init_all_marking_tasks()
        init_all_id_tasks()
