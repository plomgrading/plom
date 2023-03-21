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
        # keep a dict of tpv to image_pk of known-images. is {tpv: [pk1, pk2, pk3,...]}
        # if a given tpv shows up in a single image, then this is a normal "known" page
        # if a given tpv corresponds to multiple images then that is
        # an "internal collision", that is, we have multiple copies of
        # a given page (as encoded by its tpv) inside the current bundle.
        known_imgs = {}
        # for each known image, also keep its bundle-order - we use that to create useful
        # error messages in case of internal collisions.
        img_bundle_order = {}

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
                        # if not seen before then store as **list** [img.pk]
                        # if has been seen before then append to that list.
                        known_imgs.setdefault(tpv, []).append(img.pk)
                        img_bundle_order[img.pk] = img.bundle_order

                except ValueError as err:
                    error_imgs.append((img.pk, str(err)))

        # now look at the known-image dict for internal collisions - ie tpv with 2 or more images
        for tpv, col_list in known_imgs.items():
            if len(col_list) == 1:  # this is not a collision, so skip
                continue
            # this tpv corresponds to multiple images, so make error images for each
            # with error-message that tells the user which other images it collides
            # with - to be useful this needs the bundle-order of each image.
            for img_pk in col_list:
                error_imgs.append(
                    (
                        img_pk,
                        "Image collides with images in this bundle at positions "
                        + ", ".join(
                            str(img_bundle_order[x] + 1)
                            for x in col_list
                            if x != img_pk
                        ),
                    )
                )

        with transaction.atomic():
            # save all the known images that are not collisions.
            for tpv, img_list in known_imgs.items():
                if len(img_list) > 1:
                    # this indicates a collision, and so handled by error-images
                    continue
                img = StagingImage.objects.get(pk=img_list[0])
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
            # save all the error-pages with the error string
            for k, err_str in error_imgs:
                img = StagingImage.objects.get(pk=k)
                img.image_type = "error"
                img.save()
                ErrorStagingImage.objects.create(
                    staging_image=img, error_reason=err_str
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
                "Inconsistent public-codes - was a page from a different assessment uploaded?"
            )
        # and make sure it matches the spec
        if codes[0] != correct_public_code:
            raise ValueError(
                "Public code does not match spec - was a page from a different assessment uploaded?"
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
