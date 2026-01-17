# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Colin B. Macdonald
# Copyright (C) 2025 Aidan Murphy

from django.contrib.auth.models import User
from django.test import TestCase
from model_bakery import baker

from plom_server.Papers.models import Bundle, FixedPage, Image
from plom_server.TestingSupport.utils import config_test
from ..services import ForgiveMissingService, ManageDiscardService


class TestForgiveMissingService(TestCase):

    @config_test({"test_spec": "demo", "num_to_produce": 5})
    def setUp(self) -> None:
        pass

    def test_subs_bundle_no_images(self) -> None:
        self.assertEqual(ForgiveMissingService.get_list_of_all_missing_dnm_pages(), [])

    def test_subs_bundle_no_bundle(self) -> None:
        with self.assertRaises(Bundle.DoesNotExist):
            ForgiveMissingService.get_substitute_image(7, 4)

    def test_subs_bundle_get_non_existant_paper(self) -> None:
        with self.assertRaisesRegex(ValueError, "Paper 7 does not exist"):
            ForgiveMissingService.get_substitute_page_info(7, 4)
        user: User = baker.make(User)
        with self.assertRaisesRegex(ValueError, "Paper 7 does not exist"):
            ForgiveMissingService.forgive_missing_fixed_page(user, 7, 4)

    def test_subs_bundle_no_bundle_erase(self) -> None:
        ForgiveMissingService.erase_all_substitute_images_and_their_bundle()


class TestForgiveService(TestCase):

    # TODO: some option I can pass here to make this work?  And if so
    # TODO: document that in the utils.py thing
    # @config_test({"test_spec": "demo", "num_to_produce": 5})

    # this "string" form not used anywhere else but needed there?
    @config_test("full_demo_config.toml")
    def setUp(self) -> None:
        pass

    def test_subs_bundle_get_subs_bundle_not_made(self) -> None:
        user: User = baker.make(User)
        with self.assertRaisesRegex(Bundle.DoesNotExist, "not yet created"):
            ForgiveMissingService.forgive_missing_fixed_page(user, 1, 4)
        ForgiveMissingService.create_system_bundle_of_substitute_pages()
        ForgiveMissingService.forgive_missing_fixed_page(user, 1, 4)

    def test_subs_bundle_create_and_erase(self) -> None:
        ForgiveMissingService.create_system_bundle_of_substitute_pages()
        ForgiveMissingService.erase_all_substitute_images_and_their_bundle()

    def test_discard_and_then_forgive_missing(self) -> None:
        bundle = baker.make(Bundle, pdf_hash="qwerty")
        user: User = baker.make(User)

        ForgiveMissingService.create_system_bundle_of_substitute_pages()

        pn = 2
        pg = 3
        f = FixedPage.objects.get(paper__paper_number=pn, page_number=pg)
        img = baker.make(Image, bundle=bundle, bundle_order=0)
        f.image = img
        f.save()

        with self.assertRaisesRegex(ValueError, "already has an image"):
            ForgiveMissingService.forgive_missing_fixed_page(user, pn, pg)

        pg += 1
        f = FixedPage.objects.get(paper__paper_number=pn, page_number=pg)
        img = baker.make(Image, bundle=bundle, bundle_order=1)
        f.image = img
        f.save()

        # ensure f is missing a page, by discarding
        ManageDiscardService().discard_pushed_fixed_page(user, f.pk, dry_run=False)
        f.refresh_from_db()
        self.assertIsNone(f.image)

        ForgiveMissingService.forgive_missing_fixed_page(user, pn, pg)
        f.refresh_from_db()
        img = f.image

        # some checks about the image name, ensure the substitution really happened
        assert "__forgive" in img.original_name
        assert f"p{pg}" in img.original_name
