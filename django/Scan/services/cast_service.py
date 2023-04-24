# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Andrew Rechnitzer

from django.contrib.auth.models import User
from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist

from Scan.models import (
    StagingBundle,
    DiscardStagingImage,
    UnknownStagingImage,
)


class ScanCastService:
    """
    Functions for casting staging images to different types
    """

    # ----------------------------------------
    # Page casting
    # ----------------------------------------

    @transaction.atomic
    def discard_image_type_from_bundle(
        self, user_obj, bundle_obj, bundle_order, image_type
    ):
        if bundle_obj.pushed:
            raise ValueError("This bundle has been pushed - cannot modify it.")
        
        if image_type == "discard":
            raise ValueError("Trying to discard an already discarded bundle image.")
        if image_type not in ["unknown", "known", "extra", "error"]:
            raise ValueError(f"Image type '{image_type}' not recognised.")

        try:
            img = bundle_obj.stagingimage_set.get(bundle_order=bundle_order)
        except ObjectDoesNotExist:
            raise ValueError(f"Cannot find an image at order {bundle_order}")

        if img.image_type != image_type:
            raise ValueError(
                f"Image at position {bundle_order} is not an {'source_type'}, it is type '{img.image_type}'"
            )

        # Be very careful to update the image type when doing this sort of operation.
        img.image_type = "discard"
        # delete the old type information
        # TODO - keep more detailed history so easier to undo.
        # Hence we have this branching for time being.
        if image_type == "unknown":
            img.unknownstagingimage.delete()
            reason = f"Unknown page discarded by {user_obj.username}"
        elif image_type == "known":
            img.knownstagingimage.delete()
            reason = f"Known page discarded by {user_obj.username}"
        elif image_type == "extra":
            img.extrastagingimage.delete()
            reason = f"Extra page discarded by {user_obj.username}"
        elif image_type == "error":
            img.errorstagingimage.delete()
            reason = f"Error page discarded by {user_obj.username}"

        DiscardStagingImage.objects.create(staging_image=img, discard_reason=reason)
        img.save()

    @transaction.atomic
    def discard_image_type_from_bundle_cmd(
        self, username, bundle_name, bundle_order, image_type
    ):
        try:
            user_obj = User.objects.get(
                username__iexact=username, groups__name__in=["scanner", "manager"]
            )
        except ObjectDoesNotExist:
            raise ValueError(
                f"User '{username}' does not exist or has wrong permissions!"
            )

        try:
            bundle_obj = StagingBundle.objects.get(slug=bundle_name)
        except ObjectDoesNotExist:
            raise ValueError(f"Bundle '{bundle_name}' does not exist!")

        self.discard_image_type_from_bundle(
            user_obj, bundle_obj, bundle_order, image_type
        )

    @transaction.atomic
    def unknowify_image_type_from_bundle(
        self, user_obj, bundle_obj, bundle_order, image_type
    ):
        if bundle_obj.pushed:
            raise ValueError("This bundle has been pushed - cannot modify it.")

        if image_type == "unknown":
            raise ValueError(
                "Trying to cast 'unknown' image to and already 'unknown' bundle image."
            )
        if image_type not in ["discard", "known", "extra", "error"]:
            raise ValueError(f"Image type '{image_type}' not recognised.")

        try:
            img = bundle_obj.stagingimage_set.get(bundle_order=bundle_order)
        except ObjectDoesNotExist:
            raise ValueError(f"Cannot find an image at order {bundle_order}")

        if img.image_type != image_type:
            raise ValueError(
                f"Image at position {bundle_order} is not an {'source_type'}, it is type '{img.image_type}'"
            )

        # Be very careful to update the image type when doing this sort of operation.
        img.image_type = "unknown"
        # delete the old type information
        # TODO - keep more detailed history so easier to undo.
        # Hence we have this branching for time being.
        if image_type == "discard":
            img.discardstagingimage.delete()
            # reason = f"Discard page cast to 'unknown' by {user_obj.username}"
        elif image_type == "known":
            img.knownstagingimage.delete()
            # reason = f"Known page cast to 'unknown' by {user_obj.username}"
        elif image_type == "extra":
            img.extrastagingimage.delete()
            # reason = f"Extra page cast to 'unknown' by {user_obj.username}"
        elif image_type == "error":
            img.errorstagingimage.delete()
            # reason = f"Error page cast to 'unknown' by {user_obj.username}"

        UnknownStagingImage.objects.create(
            staging_image=img,
        )
        img.save()

    @transaction.atomic
    def unknowify_image_type_from_bundle_cmd(
        self, username, bundle_name, bundle_order, image_type
    ):
        try:
            user_obj = User.objects.get(
                username__iexact=username, groups__name__in=["scanner", "manager"]
            )
        except ObjectDoesNotExist:
            raise ValueError(
                f"User '{username}' does not exist or has wrong permissions!"
            )

        try:
            bundle_obj = StagingBundle.objects.get(slug=bundle_name)
        except ObjectDoesNotExist:
            raise ValueError(f"Bundle '{bundle_name}' does not exist!")

        self.unknowify_image_type_from_bundle(
            user_obj, bundle_obj, bundle_order, image_type
        )
