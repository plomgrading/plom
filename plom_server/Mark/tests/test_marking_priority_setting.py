# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Edith Coates
# Copyright (C) 2023-2025 Colin B. Macdonald

from django.test import TestCase

from plom_server.TestingSupport.config_test import config_test
from plom_server.Papers.models import Paper
from plom_server.TaskOrder.services import TaskOrderService

from ..models import MarkingTask
from ..services import QuestionMarkingService, MarkingPriorityService


class MarkingTaskPriorityTests(TestCase):
    """Tests for marking task priority."""

    def test_taskorder_default(self) -> None:
        strategy = MarkingPriorityService.get_mark_priority_strategy()
        # default could change, but should be one of these
        self.assertIn(strategy, ("paper_number", "shuffle"))

    @config_test()
    def test_taskorder_update(self) -> None:
        """Test task order updating.

        Config:
        test_spec = "tiny_spec.toml"
        num_to_produce = 5
        auto_init_tasks = true
        """
        TaskOrderService.update_priority_ordering("shuffle")
        strategy = MarkingPriorityService.get_mark_priority_strategy()
        self.assertEqual(strategy, "shuffle")

        custom_priority = {(1, 1): 1}
        TaskOrderService.update_priority_ordering(
            "custom", custom_order=custom_priority
        )
        strategy = MarkingPriorityService.get_mark_priority_strategy()
        self.assertEqual(strategy, "custom")

        TaskOrderService.update_priority_ordering("papernum")
        strategy = MarkingPriorityService.get_mark_priority_strategy()
        self.assertEqual(strategy, "paper_number")

    @config_test()
    def test_set_priority_papernum(self) -> None:
        """Test that PAPER_NUMBER is the default strategy.

        Config:
        test_spec = "tiny_spec.toml"
        num_to_produce = 5
        auto_init_tasks = true
        """
        n_papers = Paper.objects.count()
        tasks = MarkingTask.objects.filter(status=MarkingTask.TO_DO).prefetch_related(
            "paper"
        )
        for task in tasks:
            self.assertEqual(task.marking_priority, n_papers - task.paper.paper_number)

        MarkingPriorityService.set_marking_priority_paper_number()
        for task in tasks:
            self.assertEqual(task.marking_priority, n_papers - task.paper.paper_number)

        self.assertEqual(
            MarkingPriorityService.get_mark_priority_strategy(),
            "paper_number",
        )

    def test_set_priority_shuffle(self) -> None:
        """Test setting priority to SHUFFLE."""
        MarkingPriorityService.set_marking_piority_shuffle()
        tasks = MarkingTask.objects.filter(status=MarkingTask.TO_DO).prefetch_related(
            "paper"
        )
        for task in tasks:
            self.assertTrue(
                task.marking_priority <= 1000 and task.marking_priority >= 0
            )

        self.assertEqual(MarkingPriorityService.get_mark_priority_strategy(), "shuffle")

    def test_set_priority_custom(self) -> None:
        """Test setting priority to CUSTOM."""
        custom_order = {(1, 1): 9, (2, 1): 356, (3, 2): 0}
        MarkingPriorityService.set_marking_priority_custom(custom_order)

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

        self.assertEqual(MarkingPriorityService.get_mark_priority_strategy(), "custom")

    @config_test()
    def test_modify_priority(self) -> None:
        """Test modifying the priority of a single task.

        Config:
        test_spec = "tiny_spec.toml"
        num_to_produce = 5
        auto_init_tasks = true
        """
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
            MarkingPriorityService.get_mark_priority_strategy(),
            "paper_number",
        )

        MarkingPriorityService.modify_task_priority(last_task, 1000)
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
            MarkingPriorityService.get_mark_priority_strategy(), "paper_number"
        )
