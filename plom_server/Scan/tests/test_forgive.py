# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Colin B. Macdonald

from django.contrib.auth.models import User
from django.test import TestCase
from model_bakery import baker

from Papers.models import Bundle
from ..services import ForgiveMissingService


class TestForgiveMissingService(TestCase):
    # A bit minimal: TODO: put a spec in place and test properly

    def test_subs_bundle_no_images(self) -> None:
        self.assertEqual(ForgiveMissingService.get_list_of_all_missing_dnm_pages(), [])

    def test_subs_bundle_no_bundle(self) -> None:
        with self.assertRaises(Bundle.DoesNotExist):
            ForgiveMissingService.get_substitute_image(7, 4)

    def test_subs_bundle_get_non_existant_paper(self) -> None:
        with self.assertRaises(ValueError):
            ForgiveMissingService.get_substitute_page_info(7, 4)
        user: User = baker.make(User)
        with self.assertRaises(ValueError):
            ForgiveMissingService.forgive_missing_fixed_page(user, 7, 4)

    def test_subs_bundle_no_bundle_erase(self) -> None:
        ForgiveMissingService.erase_all_substitute_images_and_their_bundle()
