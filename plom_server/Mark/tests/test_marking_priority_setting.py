# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Edith Coates
# Copyright (C) 2023-2025 Colin B. Macdonald

from importlib import resources

from plom_server.Base.tests import ConfigTestCase
from plom_server.Papers.models import Paper
from plom_server.TaskOrder.services import TaskOrderService

from ..models import MarkingTask, MarkingTaskPriority
from ..services import QuestionMarkingService, marking_priority
from . import config_files


class MarkingTaskPriorityTests(ConfigTestCase):
    """Tests for marking task priority."""

    # mypy stumbling over Traverseable?  but abc.Traversable added in Python 3.11
    config_file = resources.files(config_files) / "priority_tests.toml"  # type: ignore[assignment]

    def test_taskorder_update(self) -> None:
        """Assert that TaskOrderService.update_priority_ordering() updates MarkingTaskPriority."""
        strategy = MarkingTaskPriority.load().strategy
        self.assertEqual(strategy, MarkingTaskPriority.PAPER_NUMBER)

        tos = TaskOrderService()
        tos.update_priority_ordering("shuffle")
        strategy = MarkingTaskPriority.load().strategy
        self.assertEqual(strategy, MarkingTaskPriority.SHUFFLE)

        custom_priority = {(1, 1): 1}
        tos.update_priority_ordering("custom", custom_order=custom_priority)
        strategy = MarkingTaskPriority.load().strategy
        self.assertEqual(strategy, MarkingTaskPriority.CUSTOM)

        tos.update_priority_ordering("papernum")
        strategy = MarkingTaskPriority.load().strategy
        self.assertEqual(strategy, MarkingTaskPriority.PAPER_NUMBER)

    def test_set_priority_papernum(self) -> None:
        """Test that PAPER_NUMBER is the default strategy."""
        n_papers = Paper.objects.count()
        tasks = MarkingTask.objects.filter(status=MarkingTask.TO_DO).prefetch_related(
            "paper"
        )
        for task in tasks:
            self.assertEqual(task.marking_priority, n_papers - task.paper.paper_number)

        marking_priority.set_marking_priority_paper_number()
        for task in tasks:
            self.assertEqual(task.marking_priority, n_papers - task.paper.paper_number)

        self.assertEqual(
            marking_priority.get_mark_priority_strategy(),
            MarkingTaskPriority.PAPER_NUMBER,
        )

    def test_set_priority_shuffle(self) -> None:
        """Test setting priority to SHUFFLE."""
        marking_priority.set_marking_piority_shuffle()
        tasks = MarkingTask.objects.filter(status=MarkingTask.TO_DO).prefetch_related(
            "paper"
        )
        for task in tasks:
            self.assertTrue(
                task.marking_priority <= 1000 and task.marking_priority >= 0
            )

        self.assertEqual(
            marking_priority.get_mark_priority_strategy(), MarkingTaskPriority.SHUFFLE
        )

    def test_set_priority_custom(self) -> None:
        """Test setting priority to CUSTOM."""
        custom_order = {(1, 1): 9, (2, 1): 356, (3, 2): 0}
        marking_priority.set_marking_priority_custom(custom_order)

        tasks = MarkingTask.objects.filter(status=MarkingTask.TO_DO).prefetch_related(
            "paper"
        )
        n_papers = Paper.objects.count()
        for task in tasks:
            task_key = (task.paper.paper_number, task.question_index)
            if task_key in custom_order.keys():
                self.assertEqual(task.marking_priority, custom_order[task_key])
            else:
                self.assertEqual(
                    task.marking_priority, n_papers - task.paper.paper_number
                )

        self.assertEqual(
            marking_priority.get_mark_priority_strategy(), MarkingTaskPriority.CUSTOM
        )

    def test_modify_priority(self) -> None:
        """Test modifying the priority of a single task."""
        n_papers = Paper.objects.count()
        tasks = MarkingTask.objects.filter(status=MarkingTask.TO_DO).prefetch_related(
            "paper"
        )
        first_task = tasks.get(paper__paper_number=1, question_index=1)
        last_task = tasks.get(paper__paper_number=5, question_index=2)

        for task in tasks:
            self.assertEqual(task.marking_priority, n_papers - task.paper.paper_number)
        self.assertEqual(QuestionMarkingService.get_first_available_task(), first_task)
        self.assertEqual(
            marking_priority.get_mark_priority_strategy(),
            MarkingTaskPriority.PAPER_NUMBER,
        )
        self.assertFalse(marking_priority.is_priority_modified())

        marking_priority.modify_task_priority(last_task, 1000)
        last_task.refresh_from_db()
        for task in tasks.all():
            if task == last_task:
                self.assertEqual(task.marking_priority, 1000)
            else:
                self.assertEqual(
                    task.marking_priority, n_papers - task.paper.paper_number
                )
        self.assertEqual(QuestionMarkingService.get_first_available_task(), last_task)
        self.assertEqual(
            marking_priority.get_mark_priority_strategy(),
            MarkingTaskPriority.PAPER_NUMBER,
        )
        self.assertTrue(marking_priority.is_priority_modified())
