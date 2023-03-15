# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Brennen Chiu
# Copyright (C) 2023 Colin B. Macdonald
# Copyright (C) 2023 Natalie Balashov
# Copyright (C) 2023 Andrew Rechnitzer

from collections import Counter
import shutil

from django.conf import settings
from django.db import transaction


from Papers.models import ErrorImage
from Papers.services import ImageBundleService, SpecificationService
from Scan.models import StagingImage, CollisionStagingImage, UnknownStagingImage


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
                        grouping_to_imgs.setdefault(grouping_key, []).append(img.pk)
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
        else:
            print("No internal collisions")

        # save the known-images so they can be pushed.
        # TODO - update this when we update the different stagingimage types
        # ie when we properly handle errors etc.
        # at present this assumes the bundle is perfect
        with transaction.atomic():
            for k, grouping_key in known_imgs:
                img = StagingImage.objects.get(pk=k)
                test_paper, page_number = self.grouping_key_to_paper_page(grouping_key)
                img.paper_id = test_paper
                img.page_number = page_number
                img.known = True
                img.save()

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

    def grouping_key_to_paper_page(self, grouping_key):
        # grouping_key is either "plomX" or "XXXXXYYYVVV"
        if len(grouping_key) != len("XXXXXYYYVVV"):
            raise ValueError(
                f"Cannot convert grouping-key {grouping_key} to paper and page"
            )
        try:
            return int(grouping_key[:5]), int(grouping_key[5:8])
        except ValueError:
            raise ValueError(
                f"Cannot convert grouping-key {grouping_key} to paper and page"
            )

    # --------------------------
    # hacked up to here....
    # --------------------------

    def check_qr_codes(self, page_data, image_path, bundle):
        """
        Check integrity of QR codes on a page.
        """

        spec_service = SpecificationService()
        spec_dictionary = spec_service.get_the_spec()
        img_obj = StagingImage.objects.get(file_path=image_path)

        serialized_top_three_qr = self.serialize_qr_code(page_data, "grouping_key")
        serialized_all_qr = self.serialize_qr_code(page_data, "TPV_code")
        serialized_public_code = self.serialize_qr_code(page_data, "public_code")

        # Disable this for the moment since it is DB intensive.
        # self.check_image_collision_within_bundle(
        # img_obj, bundle, serialized_top_three_qr, page_data
        # )

        self.check_TPV_code(
            serialized_all_qr, img_obj, serialized_top_three_qr, page_data
        )
        self.check_qr_numbers(page_data, img_obj, serialized_top_three_qr)
        self.check_qr_matching(
            serialized_top_three_qr, img_obj, serialized_top_three_qr, page_data
        )
        self.check_public_code(
            serialized_public_code,
            spec_dictionary,
            img_obj,
            serialized_top_three_qr,
            page_data,
        )

    def serialize_qr_code(self, page_data, tpv_type):
        """
        Function to serialize QR code based on tpv type.
        tpv_type:
           grouping_key:    get the top 3 tpv codes.
               TPV_code:    get all the tpv codes.
            public_code:    get tpv public codes.
        """
        qr_code_list = []
        for quadrant in page_data:
            grouping_key = page_data.get(quadrant)["grouping_key"]
            quadrant_num = page_data.get(quadrant)["quadrant"]
            public_code = page_data.get(quadrant)["public_code"]

            if tpv_type == "grouping_key":
                qr_code_list.append(grouping_key)
            elif tpv_type == "TPV_code":
                qr_code_list.append(grouping_key + quadrant_num + public_code)
            elif tpv_type == "public_code":
                qr_code_list.append(public_code)
            else:
                raise ValueError("No specific TPV type found.")

        return qr_code_list

    def check_TPV_code(self, qr_list, img_obj, top_three_tpv, page_data):
        """
        Check if TPV codes are 17 digits long.
        """
        for indx in qr_list:
            if len(indx) != len("TTTTTPPPVVVOCCCCC"):
                self.create_error_image(img_obj, top_three_tpv)
                img_obj.parsed_qr = page_data
                img_obj.error = True
                img_obj.save()
                raise ValueError("Invalid QR code.")

    def check_qr_numbers(self, page_data, img_obj, top_three_tpv):
        """
        Check number of QR codes in a given page.
        """
        if len(page_data) == 0:
            self.create_unknown_image(img_obj)
            img_obj.unknown = True
            img_obj.save()
            raise ValueError("Unable to read QR codes.")
        elif len(page_data) <= 2:
            self.create_error_image(img_obj, top_three_tpv)
            img_obj.parsed_qr = page_data
            img_obj.error = True
            img_obj.save()
            raise ValueError("Detected fewer than 3 QR codes.")
        elif len(page_data) == 3:
            pass
        else:
            self.create_error_image(img_obj, top_three_tpv)
            img_obj.parsed_qr = page_data
            img_obj.error = True
            img_obj.save()
            raise ValueError("Detected more than 3 QR codes.")

    def check_qr_matching(self, qr_list, img_obj, top_three_tpv, page_data):
        """
        Check if QR codes match.
        This is to check if a page is folded.
        """
        for indx in range(1, len(qr_list)):
            if qr_list[indx] == qr_list[indx - 1]:
                pass
            else:
                self.create_error_image(img_obj, top_three_tpv)
                img_obj.parsed_qr = page_data
                img_obj.error = True
                img_obj.save()
                raise ValueError("QR codes do not match.")

    def check_public_code(
        self, public_codes, spec_dictionary, img_obj, top_three_tpv, page_data
    ):
        """
        Check if the paper public QR code matches with spec public code.
        """
        spec_public_code = spec_dictionary["publicCode"]
        for public_code in public_codes:
            if public_code == str(spec_public_code):
                pass
            else:
                self.create_error_image(img_obj, top_three_tpv)
                img_obj.parsed_qr = page_data
                img_obj.error = True
                img_obj.save()
                raise ValueError(
                    f"Magic code {public_code} did not match spec {spec_public_code}. Did you scan the wrong test?"
                )

    def check_image_collision_within_bundle(
        self, image_obj, bundle, top_three_tpv, page_data
    ):
        all_images = StagingImage.objects.filter(bundle=bundle)
        img_hash_list = []
        img_hash_list.append(str(image_obj.image_hash))
        for img in all_images:
            img_hash_list.append(str(img.image_hash))
        count = img_hash_list.count(str(image_obj.image_hash))
        if count > 2:
            self.create_collision_image(image_obj, top_three_tpv)
            image_obj.parsed_qr = page_data
            image_obj.colliding = True
            image_obj.save()
            raise ValueError("You have duplicate pages in this bundle.")

    def create_error_image(self, img_obj, top_three_tpv):
        if not ErrorImage.objects.filter(hash=img_obj.image_hash).exists():
            img_bundle_service = ImageBundleService()
            counter = Counter(top_three_tpv)
            most_common_qr = counter.most_common(1)
            common_qr = most_common_qr[0][0]

            test_paper = common_qr[0:5]
            page_number = common_qr[5:8]
            version_number = common_qr[8:]

            root_folder = settings.MEDIA_ROOT / "page_images" / "error_pages"
            test_folder = root_folder / str(test_paper)
            img_path = test_folder / f"page{page_number}_{img_obj.image_hash}.png"

            staged_bundle = img_obj.bundle
            bundle = img_bundle_service.get_or_create_bundle(
                staged_bundle.slug, staged_bundle.pdf_hash
            )

            error_image = ErrorImage(
                bundle=bundle,
                bundle_order=img_obj.bundle_order,
                original_name=img_obj.file_name,
                file_name=str(img_path),
                hash=img_obj.image_hash,
                rotation=img_obj.rotation,
                paper_number=int(test_paper),
                page_number=int(page_number),
                version_number=int(version_number),
            )
            error_image.save()

            root_folder.mkdir(exist_ok=True)
            test_folder.mkdir(exist_ok=True)
            shutil.copy(img_obj.file_path, img_path)

    def create_collision_image(self, img_obj, top_three_tpv):
        counter = Counter(top_three_tpv)
        most_common_qr = counter.most_common(1)
        common_qr = most_common_qr[0][0]

        test_paper = common_qr[0:5]
        page_number = common_qr[5:8]
        version_number = common_qr[8:]

        collision_image = CollisionStagingImage(
            bundle=img_obj.bundle,
            bundle_order=img_obj.bundle_order,
            file_name=img_obj.file_name,
            file_path=img_obj.file_path,
            image_hash=img_obj.image_hash,
            parsed_qr=img_obj.parsed_qr,
            rotation=img_obj.rotation,
            paper_number=int(test_paper),
            page_number=int(page_number),
            version_number=int(version_number),
        )
        collision_image.save()

    def create_unknown_image(self, img_obj):
        unknown_image = UnknownStagingImage(
            bundle=img_obj.bundle,
            bundle_order=img_obj.bundle_order,
            file_name=img_obj.file_name,
            file_path=img_obj.file_path,
            image_hash=img_obj.image_hash,
            rotation=img_obj.rotation,
        )
        unknown_image.save()
