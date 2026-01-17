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

    @config_test({"test_spec": "demo", "num_to_produce": 5, "test_sources": "demo"})
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
        # Note: FixedPage.objects.get only works when no shared pages but
        # its ok here as used for testing.
        f = FixedPage.objects.get(paper__paper_number=pn, page_number=3)
        # Note: the test harness stuff currently does not populate the image
        # field.  We baker it.  Could change in the future...
        img = baker.make(Image, bundle=bundle, bundle_order=0)
        f.image = img
        f.save()

        pg = 4
        f = FixedPage.objects.get(paper__paper_number=pn, page_number=pg)
        img = baker.make(Image, bundle=bundle, bundle_order=1)
        f.image = img
        f.save()

        # setup complete, now test

        with self.assertRaisesRegex(ValueError, "already has an image"):
            ForgiveMissingService.forgive_missing_fixed_page(user, pn, 3)

        # ensure f is missing a page, by discarding
        ManageDiscardService().discard_pushed_fixed_page(user, f.pk)
        f.refresh_from_db()
        self.assertIsNone(f.image)

        ForgiveMissingService.forgive_missing_fixed_page(user, pn, pg)
        f.refresh_from_db()
        img = f.image

        # some checks about the image name, ensure the substitution really happened
        assert "__forgive" in img.original_name
        assert f"p{pg}" in img.original_name

        info = ForgiveMissingService.get_substitute_page_info(pn, pg)
        self.assertEqual(info["kind"], "QuestionPage")
        self.assertEqual(info["paper_number"], pn)
        self.assertEqual(info["page_number"], pg)


class TestForgiveServiceSharedPages(TestCase):

    @config_test(
        {
            "test_spec": "spec_with_shared_pages.toml",
            "num_to_produce": 5,
            "test_sources": "demo",
        }
    )
    def setUp(self) -> None:
        pass

    def test_discard_and_then_forgive_missing_shared_page(self) -> None:
        bundle = baker.make(Bundle, pdf_hash="qwerty")
        user: User = baker.make(User)

        ForgiveMissingService.create_system_bundle_of_substitute_pages()

        pn = 2
        pg = 3
        # page 3 is shared by 3 QuestionPages, as per the spec_with_shared_pages.toml
        fps = FixedPage.objects.filter(paper__paper_number=pn, page_number=pg)
        order = 0
        img = baker.make(Image, bundle=bundle, bundle_order=order)
        order += 1

        assert len(fps) == 3
        for f in fps:
            # Note: the test harness stuff currently does not populate the image
            # field.  We baker it.  Could change in the future...
            self.assertIsNone(f.image)
            f.image = img
            f.save()
        # note all three share the same image, as would be the case in practice

        # setup complete, now test

        with self.assertRaisesRegex(ValueError, "already has an image"):
            ForgiveMissingService.forgive_missing_fixed_page(user, pn, pg)

        # First, say if we only discard 1 out of 3 of their common shared image...
        ManageDiscardService().discard_pushed_fixed_page(user, fps[0].pk)
        ManageDiscardService().discard_pushed_fixed_page(user, fps[1].pk)
        # In this case, its still an error to try to forgive
        with self.assertRaisesRegex(ValueError, "already has an image"):
            ForgiveMissingService.forgive_missing_fixed_page(user, pn, pg)

        # Now test that it works if we discard their shared common image over all
        ManageDiscardService().discard_pushed_fixed_page(user, fps[2].pk)
        ForgiveMissingService.forgive_missing_fixed_page(user, pn, pg)

        # Next we check the results are as expected

        fps = FixedPage.objects.filter(paper__paper_number=pn, page_number=pg)
        for f in fps:
            img = f.image
            # some checks about the image name, ensure the substitution really happened
            assert "__forgive" in img.original_name
            assert f"p{pg}" in img.original_name

        # they should (probably) all share a single image
        image_ids = [f.image.id for f in fps]
        self.assertEqual(len(set(image_ids)), 1)

        info = ForgiveMissingService.get_substitute_page_info(pn, pg)
        self.assertEqual(info["kind"], "QuestionPage")
        self.assertEqual(info["paper_number"], pn)
        self.assertEqual(info["page_number"], pg)

        # the same subs image we saw three links to earlier
        self.assertEqual(info["substitute_image_pk"], image_ids[0])
