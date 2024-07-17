# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2022 Brennen Chiu
# Copyright (C) 2023-2024 Colin B. Macdonald

import sys

if sys.version_info >= (3, 10):
    from importlib import resources
else:
    import importlib_resources as resources

from django.test import TestCase, Client, RequestFactory
from django.contrib.auth.models import User, Group
from django.urls import reverse
from model_bakery import baker

from Papers.services import SpecificationService
from Papers.models import Specification
from ...views import PreparationLandingView

from ... import useful_files_for_testing as useful_files


class PreparationLandingTests(TestCase):
    """Test the preparation app landing view."""

    def setUp(self) -> None:
        """Create and force login a manager user so the client can request the page."""
        manager_user: User = baker.make(User)
        manager_group: Group = baker.make(Group, name="manager")
        manager_user.groups.add(manager_group)

        self.cli = Client()
        self.cli.force_login(manager_user)

        self.factory = RequestFactory()

    def test_reverses(self) -> None:
        """Test the expected URL path and shortcut name."""
        landing = reverse("prep_landing")
        self.assertEqual(landing, "/create/")

    def test_get(self) -> None:
        """Test getting the page when signed in."""
        response = self.cli.get(reverse("prep_landing"))
        self.assertEqual(response.status_code, 200)

    def test_default_seatbelts(self) -> None:
        """Test an empty preparation page: should only allow creating a specification."""
        landing_view = PreparationLandingView()
        context = landing_view.build_context()

        self.assertFalse(context["valid_spec"])
        self.assertFalse(context["papers_staged"])

        self.assertFalse(context["can_upload_source_tests"])
        self.assertEqual(context["num_uploaded_source_versions"], 0)

        self.assertFalse(context["prename_enabled"])

        self.assertFalse(context["student_list_present"])

        self.assertFalse(context["papers_staged"])

        self.assertFalse(context["all_papers_built"])

    def test_after_spec_made(self) -> None:
        """Test the seatbelts after a specification is saved.

        Tt should reveal source versions and QV map.
        """
        spec_path = resources.files(useful_files) / "testing_test_spec.toml"
        SpecificationService.load_spec_from_toml(spec_path)

        landing = PreparationLandingView()
        context = landing.build_context()

        self.assertTrue(context["valid_spec"])
        self.assertTrue(context["can_upload_source_tests"])

        # Remove the spec - the above settings should be false again
        Specification.objects.all().delete()

        new_context = landing.build_context()
        self.assertFalse(new_context["valid_spec"])
        self.assertFalse(new_context["can_upload_source_tests"])
