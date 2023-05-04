# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Andrew Rechnitzer

from django.contrib.auth.models import User
from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied

from Papers.models import Paper, QuestionPage
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
        """A wrapper around discard_image_type_from_bundle cmd.

        The main difference is that it that takes a
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
        if bundle_obj.pushed:
            raise ValueError("This bundle has been pushed - it cannot be modified.")

        try:
            img = bundle_obj.stagingimage_set.get(bundle_order=bundle_order)
        except ObjectDoesNotExist:
            raise ValueError(f"Cannot find an image at order {bundle_order}")

        if image_type is None:
            image_type = img.image_type
            # Notice that we can still trigger the "you are discarding a discard" error.

        if image_type == StagingImage.DISCARD:
            raise ValueError("Trying to discard an already discarded bundle image.")
        if image_type not in [
            StagingImage.UNKNOWN,
            StagingImage.KNOWN,
            StagingImage.EXTRA,
            StagingImage.ERROR,
        ]:
            raise ValueError(f"Image type '{image_type}' not recognised.")
        if img.image_type != image_type:
            raise ValueError(
                f"Image at position {bundle_order} is not an '{image_type}', it is type '{img.image_type}'"
            )

        # Be very careful to update the image type when doing this sort of operation.
        img.image_type = StagingImage.DISCARD

        # Now delete the old type information
        # TODO - keep more detailed history so easier to undo.
        # Hence we have this branching for time being.

        if image_type == StagingImage.UNKNOWN:
            img.unknownstagingimage.delete()
            reason = f"Unknown page discarded by {user_obj.username}"
        elif image_type == StagingImage.KNOWN:
            img.knownstagingimage.delete()
            reason = f"Known page discarded by {user_obj.username}"
        elif image_type == StagingImage.EXTRA:
            img.extrastagingimage.delete()
            reason = f"Extra page discarded by {user_obj.username}"
        elif image_type == StagingImage.ERROR:
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
            user_obj, bundle_obj, bundle_order, image_type=image_type
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
            image_type = img.image_type

        if image_type == StagingImage.UNKNOWN:
            raise ValueError(
                "Trying to cast 'unknown' image to and already 'unknown' bundle image."
            )
        if image_type not in [
            StagingImage.DISCARD,
            StagingImage.KNOWN,
            StagingImage.EXTRA,
            StagingImage.ERROR,
        ]:
            raise ValueError(f"Image type '{image_type}' not recognised.")
        if img.image_type != image_type:
            raise ValueError(
                f"Image at position {bundle_order} is not an '{image_type}', it is type '{img.image_type}'"
            )

        # Be very careful to update the image type when doing this sort of operation.
        img.image_type = StagingImage.UNKNOWN
        # delete the old type information
        # TODO - keep more detailed history so easier to undo.
        # Hence we have this branching for time being.
        if image_type == StagingImage.DISCARD:
            img.discardstagingimage.delete()
        elif image_type == StagingImage.KNOWN:
            img.knownstagingimage.delete()
        elif image_type == StagingImage.EXTRA:
            img.extrastagingimage.delete()
        elif image_type == StagingImage.ERROR:
            img.errorstagingimage.delete()
        else:
            raise RuntimeError("Cannot recognise image type")

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

    @transaction.atomic
    def assign_extra_page(
        self, user_obj, bundle_obj, bundle_order, paper_number, question_list
    ):
        if bundle_obj.pushed:
            raise ValueError("This bundle has been pushed - it cannot be modified.")
        # make sure paper_number in db
        try:
            paper = Paper.objects.get(paper_number=paper_number)
        except ObjectDoesNotExist:
            raise ValueError(f"Paper {paper_number} is not in the database.")
        # now check all the question-numbers
        for q in question_list:
            if not QuestionPage.objects.filter(paper=paper, question_number=q).exists():
                raise ValueError(f"No question {q} in database.")

        # at this point the paper-number and question-list are valid, so get the image at that bundle-order.
        try:
            img = bundle_obj.stagingimage_set.get(
                bundle_order=bundle_order, image_type=StagingImage.EXTRA
            )
        except ObjectDoesNotExist:
            raise ValueError(f"Cannot find an extra-page at order {bundle_order}")

        eximg = img.extrastagingimage
        eximg.paper_number = paper_number
        eximg.question_list = question_list
        eximg.save()

    @transaction.atomic
    def assign_extra_page_cmd(
        self, username, bundle_name, bundle_order, paper_number, question_list
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

        self.assign_extra_page(
            user_obj, bundle_obj, bundle_order, paper_number, question_list
        )

    @transaction.atomic
    def clear_extra_page(self, user_obj, bundle_obj, bundle_order):
        if bundle_obj.pushed:
            raise ValueError("This bundle has been pushed - it cannot be modified.")

        try:
            img = bundle_obj.stagingimage_set.get(
                bundle_order=bundle_order, image_type=StagingImage.EXTRA
            )
        except ObjectDoesNotExist:
            raise ValueError(f"Cannot find an extra-page at order {bundle_order}")

        eximg = img.extrastagingimage
        eximg.paper_number = None
        eximg.question_list = None
        eximg.save()

    @transaction.atomic
    def clear_extra_page_cmd(self, username, bundle_name, bundle_order):
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

        self.clear_extra_page(user_obj, bundle_obj, bundle_order)

    def string_to_staging_image_type(self, img_str):
        """A helper function to translate from string to the staging image enum type"""

        img_str = img_str.casefold()
        if img_str.casefold() == "discard":
            return StagingImage.DISCARD

        elif img_str.casefold() == "extra":
            return StagingImage.EXTRA

        elif img_str.casefold() == "error":
            return StagingImage.ERROR

        elif img_str.casefold() == "known":
            return StagingImage.KNOWN

        elif img_str.casefold() == "unknown":
            return StagingImage.UNKNOWN
        else:
            raise ValueError(f"Unrecognisable image type '{img_str}'")
