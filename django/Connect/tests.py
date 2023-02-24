# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2022 Colin B. Macdonald
# Copyright (C) 2023 Natalie Balashov

from datetime import datetime, timedelta
from django.utils import timezone
from django.test import TestCase
from model_bakery import baker

from Connect.services import CoreConnectionService
from Connect.models import CoreDBinitialiseTask


class CoreConnectionServiceTests(TestCase):
    """Test Connection.services.CoreConnectionService"""

    def test_get_latest_init_db_task(self):
        """Test CoreConnectionService.get_latest_running_init_db_task"""
        task1 = baker.make(
            CoreDBinitialiseTask, created=timezone.now(), status="queued"
        )
        task2 = baker.make(
            CoreDBinitialiseTask,
            created=timezone.now() + timedelta(minutes=1),
            status="running",
        )

        ccs = CoreConnectionService()
        latest = ccs.get_latest_init_db_task()
        self.assertEqual(latest.huey_id, task2.huey_id)

    def test_latest_task_returns_none(self):
        """Test that CoreConnectionService.get_latest_running_init_db_task returns none if no tasks are present."""
        ccs = CoreConnectionService()
        latest = ccs.get_latest_init_db_task()
        self.assertIsNone(latest)
