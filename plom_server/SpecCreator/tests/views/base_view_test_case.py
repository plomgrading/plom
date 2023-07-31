# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2023 Colin B. Macdonald

from django.test import TestCase, Client
from model_bakery import baker


class BaseTestSpecViewTestCase(TestCase):
    """A base test case for the test spec views."""

    def setUp(self):
        """Create/force login a dummy manager user in order to access the view."""
        self.manager_user = baker.make("User")
        self.manager_group = baker.make("Group", name="manager")
        self.manager_user.groups.add(self.manager_group)

        self.cli = Client()
        self.cli.force_login(self.manager_user)
        return super().setUp()
