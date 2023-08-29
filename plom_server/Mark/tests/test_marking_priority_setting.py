# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Edith Coates

import sys

if sys.version_info >= (3, 10):
    from importlib import resources
else:
    import importlib_resources as resources

from Base.tests import config_test, ConfigTestCase
from Mark.models import MarkingTaskPriority
from Mark.services import MarkingTaskService
from TaskOrder.services.task_ordering_service import TaskOrderService

from . import config_files


class MarkingTaskPriorityTests(ConfigTestCase):
    """Tests for the MarkingTaskPriority model."""

    config_file = resources.files(config_files) / "priority_tests.toml"

    def test_set_task_priorities(self):
        """Assert that MarkingTaskService.set_task_priorities() updates MarkingTaskPriority."""

        strategy = MarkingTaskPriority.load().strategy
        self.assertEqual(strategy, MarkingTaskPriority.PAPER_NUMBER)

        mts = MarkingTaskService()
        mts.set_task_priorities(order_by=MarkingTaskPriority.RANDOM)
        strategy = MarkingTaskPriority.load().strategy
        self.assertEqual(strategy, MarkingTaskPriority.RANDOM)

        custom_priority = {(1, 1): 1}
        mts.set_task_priorities(
            order_by=MarkingTaskPriority.CUSTOM, custom_order=custom_priority
        )
        strategy = MarkingTaskPriority.load().strategy
        self.assertEqual(strategy, MarkingTaskPriority.CUSTOM)

        with self.assertRaises(AssertionError):
            mts.set_task_priorities("unknown")
        strategy = MarkingTaskPriority.load().strategy
        self.assertEqual(strategy, MarkingTaskPriority.CUSTOM)

    def test_taskorder_update(self):
        """Assert that TaskOrderService.update_priority_ordering() updates MarkingTaskPriority."""

        strategy = MarkingTaskPriority.load().strategy
        self.assertEqual(strategy, MarkingTaskPriority.PAPER_NUMBER)

        tos = TaskOrderService()
        tos.update_priority_ordering("random")
        strategy = MarkingTaskPriority.load().strategy
        self.assertEqual(strategy, MarkingTaskPriority.RANDOM)

        custom_priority = {(1, 1): 1}
        tos.update_priority_ordering("custom", custom_order=custom_priority)
        strategy = MarkingTaskPriority.load().strategy
        self.assertEqual(strategy, MarkingTaskPriority.CUSTOM)

        tos.update_priority_ordering("papernum")
        strategy = MarkingTaskPriority.load().strategy
        self.assertEqual(strategy, MarkingTaskPriority.PAPER_NUMBER)

    def test_task_priorities_custom(self):
        """Test the behavior of the custom_priority field with MarkingTaskService."""

        custom_priority = MarkingTaskPriority.load().custom_priority
        self.assertEqual(custom_priority, {})

        mts = MarkingTaskService()
        with self.assertRaises(AssertionError):
            mts.set_task_priorities(MarkingTaskPriority.CUSTOM)

        custom_priority = {(1, 1): 1, (2, 2): 2}
        mts.set_task_priorities(
            MarkingTaskPriority.CUSTOM, custom_order=custom_priority
        )
        custom_priority = MarkingTaskPriority.load().custom_priority
        self.assertEqual(custom_priority, {"1,1": 1, "2,2": 2})

        mts.set_task_priorities(MarkingTaskPriority.PAPER_NUMBER)
        custom_priority = MarkingTaskPriority.load().custom_priority
        self.assertEqual(custom_priority, {})

    def test_taskorder_custom(self):
        """Test the behavior of the custom_priority field with TaskOrderService."""

        custom_priority = MarkingTaskPriority.load().custom_priority
        self.assertEqual(custom_priority, {})

        tos = TaskOrderService()
        with self.assertRaises(AssertionError):
            tos.update_priority_ordering("custom")

        custom_priority = {(1, 1): 1, (2, 2): 2}
        tos.update_priority_ordering("custom", custom_order=custom_priority)
        custom_priority = MarkingTaskPriority.load().custom_priority
        self.assertEqual(custom_priority, {"1,1": 1, "2,2": 2})

        tos.update_priority_ordering("papernum")
        custom_priority = MarkingTaskPriority.load().custom_priority
        self.assertEqual(custom_priority, {})
