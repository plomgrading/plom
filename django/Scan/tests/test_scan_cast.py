# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Andrew Rechnitzer


from django.test import TestCase
from django.contrib.auth.models import User, Group
from django.core.exceptions import PermissionDenied, ObjectDoesNotExist

from model_bakery import baker

from Scan.models import StagingBundle, StagingImage
from Scan.models import (
    UnknownStagingImage,
    KnownStagingImage,
    ErrorStagingImage,
    DiscardStagingImage,
    ExtraStagingImage,
)


from Scan.services import ScanCastService


class ScanCastServiceTests(TestCase):
    def make_image(self, image_type):
        # put images into first available order
        number_of_pages = self.bundle.stagingimage_set.count()
        img = baker.make(
            StagingImage,
            bundle=self.bundle,
            bundle_order=number_of_pages,
            image_type=image_type,
        )
        if image_type == "unknown":
            baker.make(UnknownStagingImage, staging_image=img)
        elif image_type == "known":
            baker.make(KnownStagingImage, staging_image=img)
        if image_type == "extra":
            baker.make(ExtraStagingImage, staging_image=img)
        if image_type == "discard":
            baker.make(DiscardStagingImage, staging_image=img)
        if image_type == "error":
            baker.make(ErrorStagingImage, staging_image=img)

    def setUp(self):
        # make scan-group, two users, one with permissions and the other not.
        scan_group = baker.make(Group, name="scanner")
        self.user0 = baker.make(User, username="user0")
        self.user0.groups.add(scan_group)
        self.user0.save()
        self.user1 = baker.make(User, username="user1")
        # make a bundle
        self.bundle = baker.make(StagingBundle, user=self.user0, slug="testbundle")
        # make some pages
        for img in [
            "unknown",
            "unknown",
            "known",
            "known",
            "extra",
            "extra",
            "discard",
            "discard",
            "error",
            "error",
        ]:
            self.make_image(img)

        return super().setUp()

    def tearDown(self):
        return super().tearDown()

    def test_permissions(self):
        scs = ScanCastService()
        # get the ord of an error page from the bundle
        ord = (
            self.bundle.stagingimage_set.filter(image_type="error").first().bundle_order
        )

        with self.assertRaises(PermissionDenied):
            scs.discard_image_type_from_bundle_cmd("user1", "testbundle", ord, "error")
        with self.assertRaises(PermissionDenied):
            scs.unknowify_image_type_from_bundle_cmd(
                "user1", "testbundle", ord, "error"
            )

        scs.discard_image_type_from_bundle_cmd("user0", "testbundle", ord, "error")
        # get the ord of another error page from the bundle
        ord = (
            self.bundle.stagingimage_set.filter(image_type="error").first().bundle_order
        )
        scs.unknowify_image_type_from_bundle_cmd("user0", "testbundle", ord, "error")

    def test_cast_to_discard(self):
        for img_type, typemodel, typestr, reason in [
            (
                "error",
                ErrorStagingImage,
                "errorstagingimage",
                "Error page discarded by user0",
            ),
            (
                "extra",
                ExtraStagingImage,
                "extrastagingimage",
                "Extra page discarded by user0",
            ),
            (
                "known",
                KnownStagingImage,
                "knownstagingimage",
                "Known page discarded by user0",
            ),
            (
                "unknown",
                UnknownStagingImage,
                "unknownstagingimage",
                "Unknown page discarded by user0",
            ),
        ]:
            # get the order of an page from the bundle
            ord = (
                self.bundle.stagingimage_set.filter(image_type=img_type)
                .first()
                .bundle_order
            )
            # grab the corresponding staging_image
            stimg = StagingImage.objects.get(bundle=self.bundle, bundle_order=ord)
            self.assertIsNotNone(getattr(stimg, typestr))
            # verify no discard image there
            with self.assertRaises(ObjectDoesNotExist):
                DiscardStagingImage.objects.get(staging_image=stimg)
            # cast it to a discard
            ScanCastService().discard_image_type_from_bundle_cmd(
                "user0", "testbundle", ord, img_type
            )
            # verify that no error image remains and that a discard image now exists
            stimg.refresh_from_db()
            with self.assertRaises(ObjectDoesNotExist):
                typemodel.objects.get(staging_image=stimg)
            # verify that a discard image exists
            self.assertIsNotNone(stimg.discardstagingimage)
            # verify discard reason
            self.assertEqual(
                reason,
                stimg.discardstagingimage.discard_reason,
            )

    def test_cast_to_unknown(self):
        for img_type, typemodel, typestr in [
            ("error", ErrorStagingImage, "errorstagingimage"),
            ("extra", ExtraStagingImage, "extrastagingimage"),
            ("known", KnownStagingImage, "knownstagingimage"),
            ("discard", DiscardStagingImage, "discardstagingimage"),
        ]:
            # get the order of an page from the bundle
            ord = (
                self.bundle.stagingimage_set.filter(image_type=img_type)
                .first()
                .bundle_order
            )
            # grab the corresponding staging_image
            stimg = StagingImage.objects.get(bundle=self.bundle, bundle_order=ord)
            self.assertIsNotNone(getattr(stimg, typestr))
            # verify no discard image there
            with self.assertRaises(ObjectDoesNotExist):
                UnknownStagingImage.objects.get(staging_image=stimg)
            # cast it to a discard
            ScanCastService().unknowify_image_type_from_bundle_cmd(
                "user0", "testbundle", ord, img_type
            )
            # verify that no error image remains and that a discard image now exists
            stimg.refresh_from_db()
            with self.assertRaises(ObjectDoesNotExist):
                typemodel.objects.get(staging_image=stimg)
            # verify that an unknown image exists
            self.assertIsNotNone(stimg.unknownstagingimage)

    def test_attempt_discard_discard(self):
        ord = (
            self.bundle.stagingimage_set.filter(image_type="discard")
            .first()
            .bundle_order
        )
        with self.assertRaises(ValueError):
            ScanCastService().discard_image_type_from_bundle_cmd("user0", "testbundle", ord, "discard")

    def test_attempt_unknowify_unknown(self):
        ord = (
            self.bundle.stagingimage_set.filter(image_type="unknown")
            .first()
            .bundle_order
        )
        with self.assertRaises(ValueError):
            ScanCastService().unknowify_image_type_from_bundle_cmd("user0", "testbundle", ord, "unknown")

    def test_attempt_modify_pushed(self):
        # set the bundle to "pushed"
        self.bundle.pushed=True
        self.bundle.save()
        # now grab an error page and attempt to modify it
        ord = (
            self.bundle.stagingimage_set.filter(image_type="error")
            .first()
            .bundle_order
        )
        with self.assertRaises(ValueError):
            ScanCastService().discard_image_type_from_bundle_cmd("user0", "testbundle", ord, "error")
        with self.assertRaises(ValueError):
            ScanCastService().unknowify_image_type_from_bundle_cmd("user0", "testbundle", ord, "error")
