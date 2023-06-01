# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Brennen Chiu

from pathlib import Path
from PIL import Image

from django.contrib.auth.models import User
from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist

from Scan.models import StagingBundle


class ImageRotateService:
    @transaction.atomic
    def rotate_image(self, user_obj, bundle_obj, bundle_order):
        if bundle_obj.pushed:
            raise ValueError("This bundle has been pushed - it cannot be modified.")

        try:
            staging_img = bundle_obj.stagingimage_set.get(bundle_order=bundle_order)
        except ObjectDoesNotExist:
            raise ValueError(f"Cannot find an image at order {bundle_order}")

        # Rotating by 90 = counter-clockwise
        staging_img.rotation += 90

        if staging_img.rotation >= 360:
            staging_img.rotation = 0

        staging_img.save()

    @transaction.atomic
    def rotate_image_cmd(self, username, bundle_name, bundle_order):
        try:
            user_obj = User.objects.get(
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

        self.rotate_image(user_obj, bundle_obj, bundle_order)
