# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Brennen Chiu
# Copyright (C) 2023 Colin B. Macdonald
# Copyright (C) 2023 Natalie Balashov
# Copyright (C) 2023 Andrew Rechnitzer

from django.db import transaction

from plom.tpv_utils import parse_paper_page_version
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
        known_imgs = []  # a normal qr-coded plom page stored as (pk, tpv)
        # keep track of all the tpv of qr-coded pages
        # to check for internal collision
        tpv_to_imgs = {}

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
                    tpv = self.get_tpv(img.parsed_qr)
                    if tpv == "plomX":  # is an extra page
                        extra_imgs.append(img.pk)
                    else:  # a normal qr-coded page
                        known_imgs.append((img.pk, tpv))
                        # keep list of imgs with this tpv to check for internal collisions
                        tpv_to_imgs.setdefault(tpv, []).append(
                            (img.pk, img.bundle_order)  # image key and its bundle-order
                        )
                except ValueError as err:
                    error_imgs.append((img.pk, err))

        # now create a dict of internal collisions from the grouping_to_imgs dict
        internal_collisions = {tpv: l for tpv, l in tpv_to_imgs.items() if len(l) > 1}
        # TODO - if any collisions, then those imgs need to be removed from "known_imgs"

        # a summary - until we actually process this stuff correctly
        print(f"No qr = {no_qr_imgs}")
        print(f"Error imgs = {error_imgs}")
        print(f"Extra imgs = {extra_imgs}")
        print(f"Known imgs = {known_imgs}")
        if len(internal_collisions) > 0:
            print(f"Internal collisions = {internal_collisions}")
            # move each colliding image from known_imgs to error_imgs
            for tpv, col_list in internal_collisions.items():
                for pk_bo in col_list:
                    error_imgs.append(
                        (
                            pk_bo[0],
                            ValueError(
                                f"Image collides with images in this bundle at positions {[x[1]+1 for x in col_list if x != pk_bo]}"
                            ),  # add one since bundle-index starts from 0 but hoomans like to start from 1.
                        )
                    )
                    # now remove this (image_key, tpv) from the know-imgs list
                    known_imgs.remove((pk_bo[0], tpv))

        else:
            print("No internal collisions")

        # save the known-images so they can be pushed.
        # TODO - update this when we update the different stagingimage types
        # ie when we properly handle errors etc.
        # at present this assumes the bundle is perfect
        with transaction.atomic():
            # save all the known images
            for k, tpv in known_imgs:
                img = StagingImage.objects.get(pk=k)
                img.image_type = "known"
                img.save()
                (
                    test_paper,
                    page_number,
                    version,
                ) = parse_paper_page_version(tpv)

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
        """Check the parsed qr-codes (typically scanned from a
        page-image) and confirm that they are both self-consistent,
        and that the publicCode matches that in the test
        specification.

        parsed_qr_dict is of the form
        {
        'NE': {'x_coord': 1419.5, 'y_coord': 139.5, 'quadrant': '1', 'page_info': {'page_num': 1, 'paper_id': 1, 'public_code': '28558', 'version_num': 1}, 'page_type': 'plom_qr', 'tpv': '00001001001', 'raw_qr_string': '00001001001128558'},
        }
        or potentially (if an extra page)
        'NE': {'x_coord': 1419.5, 'y_coord': 139.5, 'quadrant': '1', 'page_type': 'plom_extra', 'tpv': 'plomX', 'raw_qr_string': 'plomX1'},
        """

        # ------ helper function to test data consistency
        def is_list_inconsistent(lst):
            return any([X != lst[0] for X in lst])

        # ------ end helper function

        # check all page-types are the same
        page_types = [parsed_qr_dict[x]["page_type"] for x in parsed_qr_dict]
        if is_list_inconsistent(page_types):
            raise ValueError("Inconsistent qr-codes - check scan for folded pages")
        # if it is an extra page, then no further consistency checks
        if page_types[0] == "plom_extra":
            return True
        #  must be a normal qr-coded plom-page - so make sure public-code is consistent
        codes = [parsed_qr_dict[x]["page_info"]["public_code"] for x in parsed_qr_dict]
        if is_list_inconsistent(codes):
            raise ValueError(
                "Inconsistent public-codes - was a page from a different assessment uploaded"
            )
        # and make sure it matches the spec
        if codes[0] != correct_public_code:
            raise ValueError(
                "Public code does not match spec - was a page from a different assessment uploaded"
            )
        # check all the same paper_id
        if is_list_inconsistent(
            [parsed_qr_dict[x]["page_info"]["paper_id"] for x in parsed_qr_dict]
        ):
            raise ValueError("Inconsistent paper-numbers - check scan for folded pages")
        # check all the same page_number
        if is_list_inconsistent(
            [parsed_qr_dict[x]["page_info"]["page_num"] for x in parsed_qr_dict]
        ):
            raise ValueError("Inconsistent page-numbers - check scan for folded pages")
        # check all the same version_number
        if is_list_inconsistent(
            [parsed_qr_dict[x]["page_info"]["version_num"] for x in parsed_qr_dict]
        ):
            raise ValueError(
                "Inconsistent version-numbers - check scan for folded pages"
            )
        # check all the same tpv - this should not be triggered because of previous checks
        if is_list_inconsistent([parsed_qr_dict[x]["tpv"] for x in parsed_qr_dict]):
            raise ValueError("Inconsistent tpv - check scan for folded pages")
        return True

    def get_tpv(self, parsed_qr_dict):
        # since we know the codes are consistent, it is sufficient to check just one.
        # note - a little python hack to get **any** value from a dict
        return next(iter(parsed_qr_dict.values()))["tpv"]

    # --------------------------
    # hacked up to here....
    # --------------------------
