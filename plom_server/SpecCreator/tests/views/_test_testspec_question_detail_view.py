# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2023 Colin B. Macdonald

from django.urls import reverse
from model_bakery import baker

from ...services import TestSpecService
from .base_view_test_case import BaseTestSpecViewTestCase


class TestSpecCreatorQuestionDetailPageTests(BaseTestSpecViewTestCase):
    """Test the question detail page view."""

    def test_reverses(self):
        """Test that the question detail view reverses with the right name."""
        view_url = reverse("q_detail", args=(1,))
        self.assertEqual(view_url, "/create/spec/questions/1")

    def test_get_not_logged_in(self):
        """Test accessing the view when not logged in, should return a 403."""
        self.cli.logout()
        response = self.cli.get(reverse("q_detail", args=(1,)))
        self.assertEqual(response.status_code, 403)

    def test_get_wrong_group(self):
        """Test getting the view when logged in but not as a manager, should return a 403."""
        scanner_group = baker.make("Group", name="scanner")
        self.manager_user.groups.all().delete()
        self.manager_user.groups.add(scanner_group)
        response = self.cli.get(reverse("q_detail", args=(1,)))
        self.assertEqual(response.status_code, 403)

    def test_get_initial_no_question(self):
        """Test the question detail view's get_initial function without an existing question."""
        # TODO: getting this page before completing the questions page should raise an error
        # TODO: what happens when accessing an invalid question index in the URL?
        spec = TestSpecService()
        spec.set_n_questions(1)

        response = self.cli.get(reverse("q_detail", args=(1,)))
        self.assertEqual(response.status_code, 200)

        initial = response.context["form"].initial
        self.assertEqual(initial["label"], "Q1")
        self.assertEqual(initial["shuffle"], "F")

    def test_get_initial_with_question(self):
        """Test the question detail view's get_initial function with an existing question."""
        spec = TestSpecService()
        spec.set_n_questions(1)
        spec.add_question(1, "Ex.1", 2, True)

        response = self.cli.get(reverse("q_detail", args=(1,)))
        self.assertEqual(response.status_code, 200)

        initial = response.context["form"].initial
        self.assertEqual(initial["label"], "Ex.1")
        self.assertEqual(initial["shuffle"], "S")
