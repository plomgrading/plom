# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Andrew Rechnitzer

from django.contrib.auth.models import User
from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied

from Scan.models import (
    StagingBundle,
    StagingImage,
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
    def discard_image_type_from_bundle_timestamp_and_order(
        self, user_obj, bundle_timestamp, bundle_order
    ):
        """A wrapper around the discard_image_type_from_bundle
        command. The main difference is that it that takes a
        bundle-timestamp instead of a bundle-object itself. Further,
        it infers the image-type from the bundle and the bundle-order
        rather than requiring it explicitly.

        Args:
            user_obj: (obj) An instead of a django user
            bundle_timestamp: (float) The timestamp of the bundle
            bundle_order: (int) Bundle order of a page.

        Returns:
            None.

        """

        bundle_obj = StagingBundle.objects.get(
            timestamp=bundle_timestamp,
        )
        try:
            img_obj = bundle_obj.stagingimage_set.get(bundle_order=bundle_order)
        except ObjectDoesNotExist:
            raise ValueError(f"Cannot find an image at order {bundle_order}")
        self.discard_image_type_from_bundle(
            user_obj, bundle_obj, bundle_order, image_type=img_obj.image_type
        )

    @transaction.atomic
    def discard_image_type_from_bundle(
        self, user_obj, bundle_obj, bundle_order, *, image_type=None
    ):
        # Notice that image_type is a lower-case string and so not directly comparable to
        # the staging_image image_type enum choices (which are either ints or upper-case strings)
        # so care must be taken at comparison time.

        if bundle_obj.pushed:
            raise ValueError("This bundle has been pushed - it cannot be modified.")

        try:
            img = bundle_obj.stagingimage_set.get(bundle_order=bundle_order)
        except ObjectDoesNotExist:
            raise ValueError(f"Cannot find an image at order {bundle_order}")

        if (
            image_type is None
        ):  # Compute the type of the image at that position and use that.
            image_type = img.image_type.lower()
            # Notice that we can still trigger the "you are discarding a discard" error.

        # casefold the image_type string
        image_type = image_type.casefold()

        if image_type == "discard":
            raise ValueError("Trying to discard an already discarded bundle image.")
        if image_type not in ["unknown", "known", "extra", "error"]:
            raise ValueError(f"Image type '{image_type}' not recognised.")
        if img.image_type.casefold() != image_type:
            raise ValueError(
                f"Image at position {bundle_order} is not an '{image_type}', it is type '{img.image_type}'"
            )

        # Be very careful to update the image type when doing this sort of operation.
        img.image_type = StagingImage.DISCARD

        # Now delete the old type information
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
        else:
            raise RuntimeError(f"Should not be here! {image_type}")

        DiscardStagingImage.objects.create(staging_image=img, discard_reason=reason)
        img.save()

    @transaction.atomic
    def discard_image_type_from_bundle_cmd(
        self, username, bundle_name, bundle_order, *, image_type=None
    ):
        try:
            user_obj = User.objects.get(
                username__iexact=username, groups__name__in=["scanner", "manager"]
            )
        except ObjectDoesNotExist:
            raise PermissionDenied(
                f"User '{username}' does not exist or has wrong permissions!"
            )

        try:
            bundle_obj = StagingBundle.objects.get(slug=bundle_name)
        except ObjectDoesNotExist:
            raise ValueError(f"Bundle '{bundle_name}' does not exist!")

        self.discard_image_type_from_bundle(
            user_obj, bundle_obj, bundle_order, image_type=None
        )

    @transaction.atomic
    def unknowify_image_type_from_bundle(
        self, user_obj, bundle_obj, bundle_order, *, image_type=None
    ):
        if bundle_obj.pushed:
            raise ValueError("This bundle has been pushed - it cannot be modified.")
        try:
            img = bundle_obj.stagingimage_set.get(bundle_order=bundle_order)
        except ObjectDoesNotExist:
            raise ValueError(f"Cannot find an image at order {bundle_order}")

        if (
            image_type is None
        ):  # Compute the type of the image at that position and use that.
            image_type = img.image_type.lower()

        # casefold the image_type string
        image_type = image_type.casefold()

        if image_type == "unknown":
            raise ValueError(
                "Trying to cast 'unknown' image to and already 'unknown' bundle image."
            )
        if image_type.casefold() not in ["discard", "known", "extra", "error"]:
            raise ValueError(f"Image type '{image_type}' not recognised.")
        if img.image_type.casefold() != image_type:
            raise ValueError(
                f"Image at position {bundle_order} is not an '{image_type}', it is type '{img.image_type}'"
            )

        # Be very careful to update the image type when doing this sort of operation.
        img.image_type = StagingImage.UNKNOWN
        # delete the old type information
        # TODO - keep more detailed history so easier to undo.
        # Hence we have this branching for time being.
        if image_type == "discard":
            img.discardstagingimage.delete()
        elif image_type == "known":
            img.knownstagingimage.delete()
        elif image_type == "extra":
            img.extrastagingimage.delete()
        elif image_type == "error":
            img.errorstagingimage.delete()

        UnknownStagingImage.objects.create(
            staging_image=img,
        )
        img.save()

    @transaction.atomic
    def unknowify_image_type_from_bundle_cmd(
        self, username, bundle_name, bundle_order, *, image_type=None
    ):
        try:
            user_obj = User.objects.get(
                username__iexact=username, groups__name__in=["scanner", "manager"]
            )
        except ObjectDoesNotExist:
            raise PermissionDenied(
                f"User '{username}' does not exist or has wrong permissions!"
            )

        try:
            bundle_obj = StagingBundle.objects.get(slug=bundle_name)
        except ObjectDoesNotExist:
            raise ValueError(f"Bundle '{bundle_name}' does not exist!")

        self.unknowify_image_type_from_bundle(
            user_obj, bundle_obj, bundle_order, image_type=image_type
        )
