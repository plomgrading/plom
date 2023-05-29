# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Brennen Chiu

from pathlib import Path
from PIL import Image

from django.contrib.auth.models import User
from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist

from Scan.models import (StagingBundle)


class ImageRotateService:

    @transaction.atomic
    def rotate_image(self, user_obj, bundle_obj, bundle_order):
        """
        angle = 90 rotates counter-clockwise
        """
        if bundle_obj.pushed:
            raise ValueError("This bundle has been pushed - it cannot be modified.")

        try:
            staging_img = bundle_obj.stagingimage_set.get(bundle_order=bundle_order)
        except ObjectDoesNotExist:
            raise ValueError(f"Cannot find an image at order {bundle_order}")
        
        image = Image.open(staging_img.image_file)
        new_image = image.rotate(angle=90, expand=True)
        new_image.save(Path("media") / str(staging_img.image_file))
        width, height = new_image.size
        image.close()
        
        if height > width:
            img_layout = "Tall"
        else:
            img_layout = "Wide"

        return img_layout
    
    @transaction.atomic
    def rotate_image_cmd(self, username, bundle_name, bundle_order):
        try:
            user_obj = User.objects.get(username__iexact=username, groups__name__in=["scanner", "manager"])
        except ObjectDoesNotExist:
            raise PermissionError(
                f"User '{username}' does not exist or has wrong permissions!"
            )
        
        try:
            bundle_obj = StagingBundle.objects.get(slug=bundle_name)
        except ObjectDoesNotExist:
            raise ValueError(f"Bundle '{bundle_name}' does not exist!")
        
        img_layout = self.rotate_image(user_obj, bundle_obj, bundle_order)

        return img_layout