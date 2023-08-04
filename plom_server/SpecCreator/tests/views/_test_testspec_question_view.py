# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2023 Colin B. Macdonald

from django.urls import reverse
from model_bakery import baker

from .base_view_test_case import BaseTestSpecViewTestCase


class TestSpecCreatorQuestionViewTests(BaseTestSpecViewTestCase):
    """Test the question/marks page view."""

    def test_reverses(self):
        """Test that the question page reverses with the right name."""
        view_url = reverse("questions")
        self.assertEqual(view_url, "/create/spec/questions/")

    def test_get_not_logged_in(self):
        """Test accessing the view when not logged in, should return a 403."""
        self.cli.logout()
        response = self.cli.get(reverse("questions"))
        self.assertEqual(response.status_code, 403)

    def test_get_wrong_group(self):
        """Test getting the view when logged in but not as a manager, should return a 403."""
        scanner_group = baker.make("Group", name="scanner")
        self.manager_user.groups.all().delete()
        self.manager_user.groups.add(scanner_group)
        response = self.cli.get(reverse("questions"))
        self.assertEqual(response.status_code, 403)

    def test_get(self):
        """Test getting the page when signed in."""
        response = self.cli.get(reverse("questions"))
        self.assertEqual(response.status_code, 200)
