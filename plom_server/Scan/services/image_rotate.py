# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Brennen Chiu
# Copyright (C) 2023 Colin B. Macdonald
# Copyright (C) 2023 Natalie Balashov
# Copyright (C) 2023 Andrew Rechnitzer

from django.contrib.auth.models import User
from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist

from ..models import StagingBundle, StagingImage
from ..services.util import check_bundle_object_is_neither_locked_nor_pushed


class ImageRotateService:
    @transaction.atomic
    def rotate_image_from_bundle_timestamp_and_order(
        self,
        user_obj,
        bundle_timestamp,
        bundle_order,
        angle,
    ):
        """A wrapper around rotate_image_cmd.

        Args:
            user_obj: (obj) An instead of a django user.
            bundle_timestamp: (float) The timestamp of the bundle.
            bundle_order: (int) Bundle order of a page.

        Returns:
            None.

        Raises:
            PlomBundleLockedException: when the bundle is pushed or locked
            ValueError: when no image at that order in the bundle
        """
        bundle_obj = StagingBundle.objects.get(timestamp=bundle_timestamp)

        check_bundle_object_is_neither_locked_nor_pushed(bundle_obj)

        try:
            staging_img = bundle_obj.stagingimage_set.get(bundle_order=bundle_order)
        except ObjectDoesNotExist:
            raise ValueError(f"Cannot find an image at order {bundle_order}")

        self._rotate_image(staging_img.pk, angle)

    @transaction.atomic
    def rotate_image_cmd(self, username, bundle_name, bundle_order):
        try:
            User.objects.get(
                username__iexact=username, groups__name__in=["scanner", "manager"]
            )
        except ObjectDoesNotExist:
            raise PermissionError(
                f"User '{username}' does not exist or has wrong permissions!"
            )

        try:
            bundle_obj = StagingBundle.objects.get(slug=bundle_name)
        except ObjectDoesNotExist:
            raise ValueError(f"Bundle '{bundle_name}' does not exist!")

        check_bundle_object_is_neither_locked_nor_pushed(bundle_obj)

        try:
            staging_img = bundle_obj.stagingimage_set.get(bundle_order=bundle_order)
        except ObjectDoesNotExist:
            raise ValueError(f"Cannot find an image at order {bundle_order}")

        self._rotate_image(staging_img.pk, angle=-90)

    @transaction.atomic
    def _rotate_image(self, staging_img_pk, angle, **kwargs):
        try:
            staging_img = StagingImage.objects.get(pk=staging_img_pk)
        except ObjectDoesNotExist:
            raise ValueError(
                f"Cannot find an image with this pk value {staging_img_pk}"
            )

        # Rotating by 90 = counter-clockwise
        # Rotating by -90 = clockwise
        if staging_img.rotation is None:
            # if rotation has not been set yet,
            # define absolute angle
            staging_img.rotation = angle
        else:
            # otherwise append to existing angle in DB
            staging_img.rotation += angle

        # keep it in [0, 360)
        staging_img.rotation %= 360
        staging_img.save()

        self.update_thumbnail_after_rotation(staging_img, angle)
