# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023-2024 Andrew Rechnitzer
# Copyright (C) 2023-2026 Colin B. Macdonald
# Copyright (C) 2025 Aidan Murphy

from django.contrib.auth.models import User
from django.db import transaction, models
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied

from plom.plom_exceptions import PlomConflict
from plom_server.Papers.models import Paper, QuestionPage, MobilePage
from plom_server.Papers.services import PaperInfoService, SpecificationService

from ..models import StagingBundle, StagingImage
from ..services.util import check_bundle_object_is_neither_locked_nor_pushed


def _manager_or_scanner_user_from_username(username: str) -> User:
    try:
        # caution: result has duplicates until we call distinct (Issue #3727)
        user_obj = (
            User.objects.filter(
                username__iexact=username, groups__name__in=["scanner", "manager"]
            )
            .distinct()
            .get()
        )
    except ObjectDoesNotExist:
        raise PermissionDenied(
            f"User '{username}' does not exist or has wrong permissions!"
        )
    return user_obj


class ScanCastService:
    """Functions for casting staging images to different types."""

    # ----------------------------------------
    # Page casting helper function
    # ----------------------------------------

    @staticmethod
    def string_to_staging_image_type(img_str: str) -> models.TextChoices:
        """A helper function to translate from string to the staging image enum type."""
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
        elif img_str.casefold() == "unread":
            return StagingImage.UNREAD
        else:
            raise ValueError(f"Unrecognisable image type '{img_str}'")

    # ----------------------------------------
    # Page casting
    # ----------------------------------------

    @classmethod
    def discard_image_type_from_bundle_id_and_order(
        cls, user_obj: User, bundle_id: int, bundle_order: int
    ) -> None:
        """A wrapper around ``discard_image_type_from_bundle``.

        The main difference is that it that takes a
        bundle-id instead of a bundle-object itself. Further,
        it infers the image-type from the bundle and the bundle-order
        rather than requiring it explicitly.

        Args:
            user_obj: which user is doing this.
            bundle_id: which bundle.
            bundle_order: which item within the bundle.

        Returns:
            None.

        Raises:
            ValueError: cannot find either the bundle or the order.
                Also if the image has already been discarded.
        """
        try:
            bundle_obj = StagingBundle.objects.get(pk=bundle_id)
            img_obj = bundle_obj.stagingimage_set.get(bundle_order=bundle_order)
        except ObjectDoesNotExist:
            raise ValueError(
                f"Cannot find an image for bundle {bundle_id} order {bundle_order}"
            )
        cls.discard_image_type_from_bundle(
            user_obj, bundle_obj, bundle_order, image_type=img_obj.image_type
        )

    @staticmethod
    @transaction.atomic
    def discard_image_type_from_bundle(
        user_obj: User,
        bundle_obj: StagingBundle,
        bundle_order: int,
        *,
        image_type: str | None = None,
    ) -> None:
        """Discard an image from a bundle.

        Args:
            user_obj: which user.
            bundle_obj: which bundle.
            bundle_order: which item within the bundle.

        Keyword Args:
            image_type: the *current* type of the image that we wish to
                discard.  You don't need to specify this but you can as
                an additional consistency check.

        Returns:
            None.

        Raises:
            ValueError: cannot find, or already discarded.
        """
        check_bundle_object_is_neither_locked_nor_pushed(bundle_obj)

        try:
            img = bundle_obj.stagingimage_set.select_for_update().get(
                bundle_order=bundle_order
            )
        except ObjectDoesNotExist:
            raise ValueError(f"Cannot find an image at order {bundle_order}")

        if image_type is None:
            image_type = img.image_type
            # Notice that we can still trigger the "you are discarding a discard" error.

        if image_type == StagingImage.DISCARD:
            raise ValueError("Trying to discard an already discarded bundle image.")
        if image_type not in (
            StagingImage.UNKNOWN,
            StagingImage.KNOWN,
            StagingImage.EXTRA,
            StagingImage.ERROR,
        ):
            raise ValueError(f"Cannot discard an image of type '{image_type}'.")
        if img.image_type != image_type:
            raise ValueError(
                f"Image at position {bundle_order} is not an '{image_type}', it is type '{img.image_type}'"
            )

        # Now delete the old type information
        if image_type == StagingImage.UNKNOWN:
            reason = f"Unknown page discarded by {user_obj.username}"
        elif image_type == StagingImage.KNOWN:
            # TODO: or leave this info for easier undo?
            img.paper_number = None
            img.page_number = None
            img.version = None
            reason = f"Known page discarded by {user_obj.username}"
        elif image_type == StagingImage.EXTRA:
            img.paper_number = None
            img.question_idx_list = None
            reason = f"Extra page discarded by {user_obj.username}"
        elif image_type == StagingImage.ERROR:
            img.error_reason = ""
            reason = f"Error page discarded by {user_obj.username}"
        else:
            raise RuntimeError(f"Should not be here! {image_type}")

        img.history += "; " + reason
        img.image_type = StagingImage.DISCARD
        img.discard_reason = reason
        img.save()

    @classmethod
    def discard_image_type_from_bundle_cmd(
        cls,
        username: str,
        bundle_name: str,
        bundle_order: int,
        *,
        image_type: str | None = None,
    ) -> None:
        user_obj = _manager_or_scanner_user_from_username(username)
        try:
            bundle_obj = StagingBundle.objects.get(slug=bundle_name)
        except ObjectDoesNotExist:
            raise ValueError(f"Bundle '{bundle_name}' does not exist!")

        cls.discard_image_type_from_bundle(
            user_obj, bundle_obj, bundle_order, image_type=image_type
        )

    @transaction.atomic
    def discard_all_unknowns_from_bundle_id(
        self,
        user_obj: User,
        bundle_id: int,
    ) -> None:
        """Discard all unknown pages in the given bundle."""
        try:
            bundle_obj = StagingBundle.objects.get(pk=bundle_id)
        except ObjectDoesNotExist:
            raise ValueError(f"Cannot find bundle {bundle_id}")

        check_bundle_object_is_neither_locked_nor_pushed(bundle_obj)

        unknown_images = bundle_obj.stagingimage_set.filter(
            image_type=StagingImage.UNKNOWN
        ).select_for_update()
        for img in unknown_images:
            s = f"{img.get_image_type_display()} bulk discarded by {user_obj.username}"
            img.history += "; " + s
            img.image_type = StagingImage.DISCARD
            img.discard_reason = s
            img.save()

    @transaction.atomic
    def unknowify_image_type_from_bundle_id_and_order(
        self, user_obj: User, bundle_id: int, bundle_order: int
    ) -> None:
        """A wrapper around ``unknowify_image_type_from_bundle``.

        The main difference is that it that takes a
        bundle id instead of a bundle-object itself. Further,
        it infers the image-type from the bundle and the bundle-order
        rather than requiring it explicitly.

        Args:
            user_obj: which user.
            bundle_id: which bundle.
            bundle_order: which item within the bundle.

        Returns:
            None.

        Raises:
            ValueError: cannot find either the bundle or the order.
        """
        try:
            bundle_obj = StagingBundle.objects.get(pk=bundle_id)
            img_obj = bundle_obj.stagingimage_set.get(bundle_order=bundle_order)
        except ObjectDoesNotExist:
            raise ValueError(
                f"Cannot find an image for bundle {bundle_id} order {bundle_order}"
            )
        self.unknowify_image_type_from_bundle(
            user_obj, bundle_obj, bundle_order, image_type=img_obj.image_type
        )

    @transaction.atomic
    def unknowify_image_type_from_bundle(
        self,
        user_obj: User,
        bundle_obj: StagingBundle,
        bundle_order: int,
        *,
        image_type: int | None = None,
    ) -> None:
        """Cast to unknown an item ("page") from the given bundle at the given order.

        Args:
            user_obj: which user is doing this?
            bundle_obj: which bundle.
            bundle_order: which item ("page" colloquially) in the bundle.

        Keyword Args:
            image_type: this is a Enum.  So its sort of an integer but you should
                be using the symbolic Enum values from ``StagingImage``.

        Returns:
            None.
        """
        check_bundle_object_is_neither_locked_nor_pushed(bundle_obj)

        try:
            img = bundle_obj.stagingimage_set.select_for_update().get(
                bundle_order=bundle_order
            )
        except ObjectDoesNotExist:
            raise ValueError(f"Cannot find an image at order {bundle_order}")

        if image_type is None:
            # Compute the type of the image at that position and use that.
            image_type = img.image_type

        if image_type == StagingImage.UNKNOWN:
            raise ValueError(
                "Trying to 'unknowify' and already 'unknown' bundle image."
            )
        if image_type not in (
            StagingImage.DISCARD,
            StagingImage.KNOWN,
            StagingImage.EXTRA,
            StagingImage.ERROR,
        ):
            raise ValueError(f"Cannot 'unknowify' and image of type '{image_type}'.")
        if img.image_type != image_type:
            raise ValueError(
                f"Image at position {bundle_order} is not an '{image_type}', it is type '{img.image_type}'"
            )

        # delete the old type information
        if image_type == StagingImage.DISCARD:
            img.discard_reason = ""
            pass
        elif image_type == StagingImage.KNOWN:
            img.paper_number = None
            img.page_number = None
            img.version = None
            pass
        elif image_type == StagingImage.EXTRA:
            img.paper_number = None
            img.question_idx_list = None
        elif image_type == StagingImage.ERROR:
            img.error_reason = ""
        else:
            raise RuntimeError("Cannot recognise image type")

        img.history += f"; {img.get_image_type_display()} made unknown by {user_obj}"
        img.image_type = StagingImage.UNKNOWN
        img.save()

    @transaction.atomic
    def unknowify_image_type_from_bundle_cmd(
        self,
        username: str,
        bundle_name: str,
        bundle_order: int,
        *,
        image_type: int | None = None,
    ) -> None:
        user_obj = _manager_or_scanner_user_from_username(username)
        try:
            bundle_obj = StagingBundle.objects.get(slug=bundle_name)
        except ObjectDoesNotExist:
            raise ValueError(f"Bundle '{bundle_name}' does not exist!")

        self.unknowify_image_type_from_bundle(
            user_obj, bundle_obj, bundle_order, image_type=image_type
        )

    @transaction.atomic
    def unknowify_all_discards_from_bundle_id(
        self,
        user_obj: User,
        bundle_id: int,
    ) -> None:
        """Cast all discard pages in the given bundle as unknowns."""
        try:
            bundle_obj = StagingBundle.objects.get(pk=bundle_id)
        except ObjectDoesNotExist:
            raise ValueError(f"Cannot find bundle {bundle_id}")

        check_bundle_object_is_neither_locked_nor_pushed(bundle_obj)

        discard_images = bundle_obj.stagingimage_set.filter(
            image_type=StagingImage.DISCARD
        ).select_for_update()
        for img in discard_images:
            img.discard_reason = ""
            img.history += f"; bulk unknowify all discards by {user_obj}"
            img.image_type = StagingImage.UNKNOWN
            img.save()

    @staticmethod
    @transaction.atomic
    def _assign_extra_page(
        user_obj: User,
        bundle_obj: StagingBundle,
        bundle_order: int,
        paper_number: int,
        assign_to_question_indices: list[int],
    ) -> None:
        """Fill in the missing information in a Extra StagingImage.

        The command assigns the paper-number and question list to the
        given extra page.

        Args:
            user_obj (django auth user database mode instance): the database
                model instance representing the user assigning information.
            bundle_obj (django staging bundle database mode instance): the
                database model instance representing the bundle being
                processed.
            bundle_order: which page of the bundle to edit, 1-indexed.
            paper_number: which paper.
            assign_to_question_indices: which questions, by a list of
                one-based indices should we assign this discarded paper to.

        Raises:
            ValueError: can't find things.
            PlomConflict: extra page already has information.
            PlomBundleLockedException:
        """
        check_bundle_object_is_neither_locked_nor_pushed(bundle_obj)

        try:
            paper = Paper.objects.get(paper_number=paper_number)
        except ObjectDoesNotExist:
            raise ValueError(f"Paper {paper_number} is not in the database.")

        # check all the questions
        # TODO: consider using question_list_utils.check_question_list: fewer DB hits?
        if False:
            for qi in assign_to_question_indices:
                if not QuestionPage.objects.filter(
                    paper=paper, question_index=qi
                ).exists():
                    raise ValueError(f"No question index {qi} in database.")
        else:
            nq = SpecificationService.get_n_questions()
            if any(
                qi < 1 or qi > nq for qi in assign_to_question_indices
            ) and assign_to_question_indices != [MobilePage.DNM_qidx]:
                raise ValueError(
                    f"Question list {assign_to_question_indices} deemed invalid."
                )

        # at this point the paper-number and question-list are valid, so get the image at that bundle-order.
        try:
            eximg = (
                bundle_obj.stagingimage_set.filter(
                    bundle_order=bundle_order, image_type=StagingImage.EXTRA
                )
                .select_for_update()
                .get()
            )
        except ObjectDoesNotExist:
            raise ValueError(f"Cannot find an extra-page at order {bundle_order}")

        # Throw value error if data has already been set.
        if eximg.paper_number is not None:
            raise PlomConflict(
                "Cannot overwrite existing extra-page info; "
                "potentially another user has set data."
            )

        eximg.paper_number = paper_number
        eximg.question_idx_list = assign_to_question_indices
        eximg.history += (
            f"; Extra information {paper_number}, {assign_to_question_indices}"
            f" provided by {user_obj}"
        )
        eximg.save()

    @classmethod
    def assign_extra_page_from_bundle_id_and_order(
        cls,
        user_obj: User,
        bundle_id: int,
        bundle_order: int,
        paper_number: int,
        assign_to_question_indices: list[int],
    ) -> None:
        """Fill in the missing information in a Extra StagingImage from bundle id.

        This is a wrapper around the actual service command
        :method:`_assign_extra_page` that does the work.

        Raises:
            ValueError: can't find things.
            PlomConflict: extra page already has information.
            PlomBundleLockedException:
        """
        try:
            bundle_obj = StagingBundle.objects.get(pk=bundle_id)
        except StagingBundle.DoesNotExist:
            raise ValueError(f"Bundle id {bundle_id} does not exist")
        cls._assign_extra_page(
            user_obj,
            bundle_obj,
            bundle_order,
            paper_number,
            assign_to_question_indices,
        )

    @classmethod
    def assign_extra_page_cmd(
        cls,
        username: str,
        bundle_name: str,
        bundle_order: int,
        paper_number: int,
        assign_to_question_indices: list[int],
    ) -> None:
        """Fill in the missing information in a Extra StagingImage.

        The command assigns the paper-number and question list to the
        given extra page.

        This is a wrapper around the actual service command
        :method:`_assign_extra_page` that does the work. Note that
        here we pass username and ``bundle_name`` as
        strings, while the :method:`_assign_extra_page` takes the corresponding
        data-base objects.

        Args:
            username (str): the name of the user who is assigning the info
            bundle_name (str): the name of the bundle being processed
            bundle_order (int): which page of the bundle to edit.
                Is 1-indexed.
            paper_number: which paper.
            assign_to_question_indices: which questions, by a list of
                one-based indices should we assign this discarded paper to.

        Raises:
            ValueError: can't find things.
            PlomConflict: extra page already has information.
            PermissionDenied: username does not exist or wrong group.
        """
        user_obj = _manager_or_scanner_user_from_username(username)

        try:
            bundle_obj = StagingBundle.objects.get(slug=bundle_name)
        except ObjectDoesNotExist:
            raise ValueError(f"Bundle '{bundle_name}' does not exist!")

        cls._assign_extra_page(
            user_obj,
            bundle_obj,
            bundle_order,
            paper_number,
            assign_to_question_indices,
        )

    @classmethod
    def clear_extra_page_info_from_bundle_id_and_order(
        cls, user_obj: User, bundle_id: int, bundle_order: int
    ) -> None:
        """A wrapper around clear_image_type.

        The main difference is that it that takes a
        bundle-id instead of a bundle-object itself. Further,
        it infers the image-type from the bundle and the bundle-order
        rather than requiring it explicitly.

        Args:
            user_obj: An instead of a django user
            bundle_id: The id of the bundle
            bundle_order: Bundle "order" specifies a page.

        Returns:
            None.
        """
        bundle_obj = StagingBundle.objects.get(pk=bundle_id)
        cls.clear_extra_page(user_obj, bundle_obj, bundle_order)

    @staticmethod
    @transaction.atomic
    def clear_extra_page(
        user_obj: User, bundle_obj: StagingBundle, bundle_order: int
    ) -> None:
        check_bundle_object_is_neither_locked_nor_pushed(bundle_obj)

        try:
            img = bundle_obj.stagingimage_set.select_for_update().get(
                bundle_order=bundle_order, image_type=StagingImage.EXTRA
            )
        except ObjectDoesNotExist:
            raise ValueError(f"Cannot find an extra-page at order {bundle_order}")

        img.paper_number = None
        img.question_idx_list = None
        img.history += f"; Extra page info cleared by {user_obj}"
        img.save()

    @classmethod
    @transaction.atomic
    def clear_extra_page_cmd(
        cls, username: str, bundle_name: str, bundle_order: int
    ) -> None:
        user_obj = _manager_or_scanner_user_from_username(username)

        try:
            bundle_obj = StagingBundle.objects.get(slug=bundle_name)
        except ObjectDoesNotExist:
            raise ValueError(f"Bundle '{bundle_name}' does not exist!")

        cls.clear_extra_page(user_obj, bundle_obj, bundle_order)

    @classmethod
    def extralise_image_from_bundle_id(
        cls, user_obj: User, bundle_id: int, bundle_order: int
    ) -> None:
        """A wrapper around extralise_image_from_bundle taking a bundle id instead of bundle object.

        Raises the same things as :method:`extralise_image_from_bundle`
        but also StagingBundle.DoesNotExist the bundle id is invalid.
        """
        bundle_obj = StagingBundle.objects.get(pk=bundle_id)
        # TODO: or ValueError, see also Issue #3878
        # try:
        #     bundle_obj = StagingBundle.objects.get(pk=bundle_id)
        # except ObjectDoesNotExist:
        #     raise ValueError(f"Bundle id {bundle_id} does not exist!")
        cls.extralise_image_from_bundle(user_obj, bundle_obj, bundle_order)

    @staticmethod
    @transaction.atomic
    def extralise_image_from_bundle(
        user_obj: User,
        bundle_obj: StagingBundle,
        bundle_order: int,
        *,
        image_type: str | None = None,
    ) -> None:
        """Cast a page image from a staged bundle to an extra page.

        This operation only succeeds for certain page image types.
        For example, if the page image is already an 'EXTRA',
        casting it to a 'EXTRA', even with a different paper and/or
        page number will fail.

        Args:
            user_obj: An instance of a django user.
            bundle_obj: The StagingBundle object containing the page image.
            bundle_order: The page image's (1-based) index in bundle_obj.

        Keyword Args:
            image_type: the current image type, mostly for you to ensure
                correctness of what you expect the data to be.  If omitted
                or None, we'll compute it.  If provided, we'll check that
                it matches reality.

        Returns:
            None.

        Raises:
            ValueError: Provided bundle_order doesn't map to a page image in
                the provided bundle_obj.  The page image type forbids it from
                being cast to a known page, or the provided image type doesn't
                match.
            PlomBundleLockedException: The bundle has already been pushed, or is
                in use by other resources.
        """
        check_bundle_object_is_neither_locked_nor_pushed(bundle_obj)

        try:
            img = bundle_obj.stagingimage_set.select_for_update().get(
                bundle_order=bundle_order
            )
        except ObjectDoesNotExist:
            raise ValueError(f"Cannot find an image at order {bundle_order}")

        if image_type is None:
            # Compute the type of the image at that position and use that.
            image_type = img.image_type

        if image_type == StagingImage.EXTRA:
            raise ValueError("Trying to 'extralise' an already 'extra' bundle image.")
        if image_type not in (
            StagingImage.DISCARD,
            StagingImage.KNOWN,
            StagingImage.UNKNOWN,
            StagingImage.ERROR,
        ):
            raise ValueError(f"Cannot 'extralise' an image of type '{image_type}'.")
        if img.image_type != image_type:
            raise ValueError(
                f"Image at position {bundle_order} is not an '{image_type}', it is type '{img.image_type}'"
            )

        # delete the old type information
        if image_type == StagingImage.DISCARD:
            img.discard_reason = ""
            pass
        elif image_type == StagingImage.KNOWN:
            # TODO: maybe we can leave the paper_number in place as EXTRA can use it
            # TODO: careful, would need overhaul, see `models/image_staging.py`
            img.paper_number = None
            img.page_number = None
            img.version = None
        elif image_type == StagingImage.UNKNOWN:
            pass
        elif image_type == StagingImage.ERROR:
            img.error_reason = ""
        else:
            raise RuntimeError("Cannot recognise image type")

        img.history += f"; {img.get_image_type_display()} made extra by {user_obj}"
        img.image_type = StagingImage.EXTRA
        # TODO: if it had a paper_number already should we keep it?
        img.paper_number = None
        img.question_idx_list = None
        img.save()

    @classmethod
    def extralise_image_from_bundle_cmd(
        cls,
        username: str,
        bundle_name: str,
        bundle_order: int,
        *,
        image_type: str | None = None,
    ) -> None:
        user_obj = _manager_or_scanner_user_from_username(username)

        try:
            bundle_obj = StagingBundle.objects.get(slug=bundle_name)
        except ObjectDoesNotExist:
            raise ValueError(f"Bundle '{bundle_name}' does not exist!")

        cls.extralise_image_from_bundle(
            user_obj, bundle_obj, bundle_order, image_type=image_type
        )

    def knowify_image_from_bundle_id(
        self,
        user_obj: User,
        bundle_id: int,
        bundle_order: int,
        paper_number: int,
        page_number: int,
    ) -> None:
        """A wrapper around knowify_image_from_bundle taking a bundle id instead of bundle object.

        Raises the same things as :method:`knowify_image_from_bundle` but
        can also raise ValueError when the bundle does not exist.
        """
        try:
            bundle_obj = StagingBundle.objects.get(pk=bundle_id)
        except ObjectDoesNotExist:
            raise ValueError(f"Bundle id {bundle_id} does not exist!")

        self.knowify_image_from_bundle(
            user_obj,
            bundle_obj,
            bundle_order,
            paper_number,
            page_number,
        )

    @transaction.atomic
    def knowify_image_from_bundle(
        self,
        user_obj: User,
        bundle_obj: StagingBundle,
        bundle_order: int,
        paper_number: int,
        page_number: int,
    ) -> None:
        """Cast a page image from a staged bundle to a known page.

        This operation only succeeds for certain page image types.
        For example, if the page image is already a 'KNOWN',
        casting it to a 'KNOWN' with a different paper and/or page
        number will fail.

        Args:
            user_obj: An instance of a django user.
            bundle_obj: The StagingBundle object containing the page image.
            bundle_order: The page image's (1-based) index in bundle_obj.
            paper_number: Set page image as known-page with this paper number.
            page_number: Set page image as known-page with this page number.

        Returns:
            None.

        Raises:
            ValueError: Provided bundle_order doesn't map to a page image in
                the provided bundle_obj. A page image already exists for
                the specified paper_number and page_number. Or, the page
                image type forbids it from being cast to a known page.
            PlomBundleLockedException: The bundle has already been pushed, or is
                in use by other resources.
        """
        check_bundle_object_is_neither_locked_nor_pushed(bundle_obj)

        try:
            img = bundle_obj.stagingimage_set.select_for_update().get(
                bundle_order=bundle_order
            )
        except ObjectDoesNotExist:
            raise ValueError(f"Cannot find an image at order {bundle_order}")

        # now check if this paper/page in the current bundle
        bundle_known_img = bundle_obj.stagingimage_set.filter(
            image_type=StagingImage.KNOWN
        )
        if bundle_known_img.filter(
            paper_number=paper_number, page_number=page_number
        ).exists():
            raise ValueError(
                f"There is already an image in this bundle with paper = {paper_number}, page = {page_number}"
            )
        # okay - now it is safe to cast the current image to a known page
        if img.image_type == StagingImage.DISCARD:
            img.discard_reason = ""
        elif img.image_type == StagingImage.UNKNOWN:
            pass
        elif img.image_type == StagingImage.ERROR:
            img.error_reason = ""
        else:
            raise ValueError(
                f"Cannot knowify an image of type {img.image_type}. Permitted types are 'DISCARD', 'UNKNOWN', and 'ERROR'"
            )

        version_in_db = PaperInfoService.get_version_from_paper_page(
            paper_number, page_number
        )
        img.paper_number = paper_number
        img.page_number = page_number
        img.version = version_in_db
        img.history += (
            f"; {img.get_image_type_display()} made known"
            f" ({paper_number}, {page_number}, {version_in_db})"
            f" by {user_obj}"
        )
        img.image_type = StagingImage.KNOWN
        img.save()

    def knowify_image_from_bundle_name(
        self,
        username: str,
        bundle_name: str,
        bundle_order: int,
        paper_number: int,
        page_number: int,
    ) -> None:
        """A wrapper around knowify_image_from_bundle taking a bundle name and user name instead of objects.

        Raises the same things as :method:`knowify_image_from_bundle` but
        can also raise ValueError when the bundle does not exist.
        """
        user_obj = _manager_or_scanner_user_from_username(username)

        # TODO: check if the underlying method would ValueError here...
        if page_number < 0 or page_number > SpecificationService.get_n_pages():
            raise ValueError("Page number out of range - check the specification")
        if paper_number < 0:
            raise ValueError("Paper number cannot be negative.")

        try:
            bundle_obj = StagingBundle.objects.get(slug=bundle_name)
        except ObjectDoesNotExist:
            raise ValueError(f"Bundle '{bundle_name}' does not exist!")

        self.knowify_image_from_bundle(
            user_obj, bundle_obj, bundle_order, paper_number, page_number
        )
