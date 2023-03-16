# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Brennen Chiu
# Copyright (C) 2023 Colin B. Macdonald
# Copyright (C) 2023 Natalie Balashov
# Copyright (C) 2023 Andrew Rechnitzer

from django.db import transaction


from Papers.services import SpecificationService
from Scan.models import (
    StagingImage,
    UnknownStagingImage,
    KnownStagingImage,
    ExtraStagingImage,
    ErrorStagingImage,
)


class QRErrorService:
    def check_read_qr_codes(self, bundle):
        # Steps
        # * flag images with no qr-codes
        # * check all images have consistent qr-codes
        # * check all images have correct public-key
        # * check all distinct test/page/version

        spec_dictionary = SpecificationService().get_the_spec()

        # lists of various image types
        no_qr_imgs = []  # no qr-codes could be read
        error_imgs = []  # indicative of a serious error (eg inconsistent qr-codes)
        extra_imgs = []  # extra-page
        known_imgs = []  # a normal qr-coded plom page stored as (pk, partial-tpv)
        # keep track of all the grouping_keys of qr-coded pages
        # to check for internal collision
        grouping_to_imgs = {}

        with transaction.atomic():
            images = bundle.stagingimage_set.all()
            for img in images:
                if len(img.parsed_qr) == 0:
                    # no qr-codes found.
                    no_qr_imgs.append(img.pk)
                    continue

                try:
                    self.check_consistent_qr(
                        img.parsed_qr, spec_dictionary["publicCode"]
                    )
                    grouping_key = self.get_grouping_key(img.parsed_qr)
                    if grouping_key == "plomX":  # is an extra page
                        extra_imgs.append(img.pk)
                    else:  # a normal qr-coded page
                        known_imgs.append((img.pk, grouping_key))
                        # keep list of imgs with this grouping-key to check for internal collisions
                        grouping_to_imgs.setdefault(grouping_key, []).append(
                            (img.pk, img.bundle_order)  # image key and its bundle-order
                        )
                except ValueError as err:
                    error_imgs.append((img.pk, err))

        # now create a dict of internal collisions from the grouping_to_imgs dict
        internal_collisions = {g: l for g, l in grouping_to_imgs.items() if len(l) > 1}
        # TODO - if any collisions, then those imgs need to be removed from "known_imgs"

        # a summary - until we actually process this stuff correctly
        print(f"No qr = {no_qr_imgs}")
        print(f"Error imgs = {error_imgs}")
        print(f"Extra imgs = {extra_imgs}")
        print(f"Known imgs = {known_imgs}")
        if len(internal_collisions) > 0:
            print(f"Internal collisions = {internal_collisions}")
            # move each colliding image from known_imgs to error_imgs
            for grp, col_list in internal_collisions.items():
                for pk_bo in col_list:
                    error_imgs.append(
                        (
                            pk_bo[0],
                            ValueError(
                                f"Image collides with images in this bundle at positions {[x[1] for x in col_list if x != pk_bo]}"
                            ),
                        )
                    )
                    # now remove this (image_key, grouping_key) from the know-imgs list
                    known_imgs.remove((pk_bo[0], grp))

        else:
            print("No internal collisions")

        # save the known-images so they can be pushed.
        # TODO - update this when we update the different stagingimage types
        # ie when we properly handle errors etc.
        # at present this assumes the bundle is perfect
        with transaction.atomic():
            # save all the known images
            for k, grouping_key in known_imgs:
                img = StagingImage.objects.get(pk=k)
                img.image_type = "known"
                img.save()
                (
                    test_paper,
                    page_number,
                    version,
                ) = self.grouping_key_to_paper_page_version(grouping_key)
                KnownStagingImage.objects.create(
                    staging_image=img,
                    paper_number=test_paper,
                    page_number=page_number,
                    version=version,
                )
            # save all the images with no-qrs.
            for k in no_qr_imgs:
                img = StagingImage.objects.get(pk=k)
                img.image_type = "unknown"
                img.save()
                UnknownStagingImage.objects.create(staging_image=img)
            # save all the extra-pages.
            for k in extra_imgs:
                img = StagingImage.objects.get(pk=k)
                img.image_type = "extra"
                img.save()
                ExtraStagingImage.objects.create(staging_image=img)
            # save all the error-pages.
            for k, err in error_imgs:
                img = StagingImage.objects.get(pk=k)
                img.image_type = "error"
                img.save()
                ErrorStagingImage.objects.create(
                    staging_image=img, error_reason=f"{err}"
                )

    def check_consistent_qr(self, parsed_qr_dict, correct_public_code):
        """parsed_qr_dict is of the form
        {
        'NE': {'x_coord': 1419.5, 'y_coord': 139.5, 'quadrant': '1', 'page_info': {'page_num': 1, 'paper_id': 1, 'public_code': '28558', 'version_num': 1}, 'page_type': 'plom_qr', 'grouping_key': '00001001001', 'tpv_signature': '00001001001128558'},
        }
        or potentially (if an extra page)
        'NE': {'x_coord': 1419.5, 'y_coord': 139.5, 'quadrant': '1', 'page_type': 'plom_extra', 'grouping_key': 'plomX', 'tpv_signature': 'plomX1'},
        """

        # ------ helper function to test data consistency
        def is_list_inconsistent(lst):
            return any([X != lst[0] for X in lst])

        # ------ end helper function

        # check all page-types are the same
        page_types = [parsed_qr_dict[x]["page_type"] for x in parsed_qr_dict]
        if is_list_inconsistent(page_types):
            raise ValueError("Inconsistent qr-codes")
        # if it is an extra page, then no further consistency checks
        if page_types[0] == "plom_extra":
            return True
        #  must be a normal qr-coded plom-page - so make sure public-code is consistent
        codes = [parsed_qr_dict[x]["page_info"]["public_code"] for x in parsed_qr_dict]
        if is_list_inconsistent(codes):
            raise ValueError("Inconsistent public-codes")
        # and make sure it matches the spec
        if codes[0] != correct_public_code:
            raise ValueError("Public code does not match spec")
        # check all the same paper_id
        if is_list_inconsistent(
            [parsed_qr_dict[x]["page_info"]["paper_id"] for x in parsed_qr_dict]
        ):
            raise ValueError("Inconsistent paper-numbers")
        # check all the same page_number
        if is_list_inconsistent(
            [parsed_qr_dict[x]["page_info"]["page_num"] for x in parsed_qr_dict]
        ):
            raise ValueError("Inconsistent page-numbers")
        # check all the same version_number
        if is_list_inconsistent(
            [parsed_qr_dict[x]["page_info"]["version_num"] for x in parsed_qr_dict]
        ):
            raise ValueError("Inconsistent version-numbers")
        # check all the same grouping_key - this should not be triggered because of previous checks
        if is_list_inconsistent(
            [parsed_qr_dict[x]["grouping_key"] for x in parsed_qr_dict]
        ):
            raise ValueError("Inconsistent grouping-keys")
        return True

    def get_grouping_key(self, parsed_qr_dict):
        # since we know the codes are consistent, it is sufficient to check just one.
        # note - a little python hack to get **any** value from a dict
        return next(iter(parsed_qr_dict.values()))["grouping_key"]

    def grouping_key_to_paper_page_version(self, grouping_key):
        # grouping_key is either "plomX" or "XXXXXYYYVVV"
        if len(grouping_key) != len("XXXXXYYYVVV"):
            raise ValueError(
                f"Cannot convert grouping-key {grouping_key} to paper and page"
            )
        try:
            return (
                int(grouping_key[:5]),
                int(grouping_key[5:8]),
                int(grouping_key[9:12]),
            )
        except ValueError:
            raise ValueError(
                f"Cannot convert grouping-key {grouping_key} to paper, page and version"
            )

    # --------------------------
    # hacked up to here....
    # --------------------------
