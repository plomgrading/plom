# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates

import toml

from django.test import TestCase, Client, RequestFactory
from django.contrib.auth.models import User, Group
from django.urls import reverse
from django.conf import settings
from model_bakery import baker

from Preparation.views import PreparationLandingView
from Papers.models import Specification


class PreparationLandingTests(TestCase):
    """
    Test the preparation app landing view.
    """

    def setUp(self):
        """Create and force login a manager user so the client can request the page."""
        self.manager_user = baker.make(User)
        self.manager_group = baker.make(Group, name="manager")
        self.manager_user.groups.add(self.manager_group)

        self.cli = Client()
        self.cli.force_login(self.manager_user)

        self.factory = RequestFactory()
        return super().setUp()

    def test_reverses(self):
        """Test the expected URL path and shortcut name"""
        landing = reverse("prep_landing")
        self.assertEqual(landing, "/create/")

    def test_get(self):
        """Test getting the page when signed in."""
        response = self.cli.get(reverse("prep_landing"))
        self.assertEqual(response.status_code, 200)

    def test_default_seatbelts(self):
        """
        Test an empty preparation page: should only allow creating
        a specification.
        """
        landing_view = PreparationLandingView()
        context = landing_view.build_context()

        self.assertFalse(context["valid_spec"])
        self.assertFalse(context["papers_staged"])

        self.assertFalse(context["can_upload_source_tests"])
        self.assertEqual(context["uploaded_test_versions"], 0)

        self.assertFalse(context["prename_enabled"])

        self.assertFalse(context["student_list_present"])

        self.assertFalse(context["pqv_mapping_present"])
        self.assertFalse(context["can_qvmap"])

        self.assertFalse(context["papers_built"])

    def test_after_spec_made(self):
        """
        Test the seatbelts after a specification is saved - it should reveal
        source versions and QV map.
        """
        demo_spec = toml.load(
            settings.BASE_DIR / "useful_files_for_testing" / "testing_test_spec.toml"
        )
        baker.make(Specification, spec_dict=demo_spec)

        landing = PreparationLandingView()
        context = landing.build_context()

        self.assertTrue(context["valid_spec"])
        self.assertTrue(context["can_upload_source_tests"])
        self.assertTrue(context["can_qvmap"])

        # Remove the spec - the above settings should be false again
        Specification.objects.all().delete()

        new_context = landing.build_context()
        self.assertFalse(new_context["valid_spec"])
        self.assertFalse(new_context["can_upload_source_tests"])
        self.assertFalse(new_context["can_qvmap"])
