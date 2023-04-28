# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2022-2023 Brennen Chiu
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2023 Colin B. Macdonald
# Copyright (C) 2023 Natalie Balashov

from collections import defaultdict
import hashlib
import pathlib
import random
from statistics import mode
import tempfile

import fitz
from django.conf import settings
from django.contrib.auth.models import User
from django.core.files import File
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.db.models import Q  # for queries involving "or", "and"
from django.db.models import Prefetch
from django_huey import db_task
from django.utils import timezone


from plom.scan import QRextract
from plom.scan import render_page_to_bitmap
from plom.scan.scansToImages import make_mucked_up_jpeg
from plom.scan.readQRCodes import checkQRsValid
from plom.scan.question_list_utils import check_question_list
from plom.scan.question_list_utils import canonicalize_page_question_map
from plom.tpv_utils import (
    parseTPV,
    parseExtraPageCode,
    getPaperPageVersion,
    isValidTPV,
    isValidExtraPageCode,
)

from .image_process import PageImageProcessor
from Scan.models import (
    StagingBundle,
    StagingImage,
    KnownStagingImage,
    ExtraStagingImage,
    DiscardStagingImage,
    ManagePageToImage,
    ManageParseQR,
)
from Papers.models import Paper
from Papers.services import ImageBundleService
from Papers.services import SpecificationService

from Scan.services.qr_validators import QRErrorService


class ScanService:
    """
    Functions for staging scanned test-papers.
    """

    def upload_bundle(
        self,
        uploaded_pdf_file,
        slug,
        user,
        timestamp,
        pdf_hash,
        number_of_pages,
        *,
        debug_jpeg=False,
    ):
        """
        Upload a bundle PDF and store it in the filesystem + database.
        Also, split PDF into page images + store in filesystem and database.

        Args:
            upload_pdf_file (Django File): File-object containing the pdf (can also be a TemporaryUploadedFile or InMemoryUploadedFile)
            slug (str): Filename slug for the pdf
            user (Django User): the user uploading the file
            timestamp (datetime): the datetime at which the file was uploaded
            pdf_hash (str): the sha256 of the pdf.
            number_of_pages (int): the number of pages in the pdf

        Keyword Args:
            debug_jpeg (bool): off by default.  If True then we make some rotations by
            non-multiplies of 90, and save some low-quality jpegs.
        """

        fh = uploaded_pdf_file.open()
        with transaction.atomic():
            bundle_obj = StagingBundle.objects.create(
                slug=slug,
                pdf_file=File(fh, name=f"{timestamp}.pdf"),
                user=user,
                timestamp=timestamp,
                number_of_pages=number_of_pages,
                pdf_hash=pdf_hash,
                pushed=False,
            )

        self.split_and_save_bundle_images(bundle_obj.pk, debug_jpeg=debug_jpeg)

    @transaction.atomic
    def upload_bundle_cmd(
        self,
        pdf_file_path,
        slug,
        username,
        timestamp,
        hashed,
        number_of_pages,
        *,
        debug_jpeg=False,
    ):
        """
        Wrapper around upload_bundle for use by the commandline bundle upload command.

        Checks if the supplied username has permissions to access and upload scans.

        Args:
            pdf_file_path (pathlib.Path or str): the path to the pdf being uploaded
            slug (str): Filename slug for the pdf
            username (str): the username uploading the file
            timestamp (datetime): the datetime at which the file was uploaded
            pdf_hash (str): the sha256 of the pdf.
            number_of_pages (int): the number of pages in the pdf

        """
        # username => user_object, if in scanner group, else exception raised.
        try:
            user_obj = User.objects.get(
                username__iexact=username, groups__name="scanner"
            )
        except ObjectDoesNotExist:
            raise ValueError(
                f"User '{username}' does not exist or has wrong permissions!"
            )

        with open(pdf_file_path, "rb") as fh:
            pdf_file_object = File(fh)

        self.upload_bundle(
            pdf_file_object,
            slug,
            user_obj,
            timestamp,
            hashed,
            number_of_pages,
            debug_jpeg=debug_jpeg,
        )

    def split_and_save_bundle_images(self, bundle_pk, *, debug_jpeg=False):
        """
        Read a PDF document and save page images to filesystem/database

        Args:
            bundle_pk: StagingBundle object primary key
        """
        bundle_obj = StagingBundle.objects.get(pk=bundle_pk)
        task = huey_parent_split_bundle_task(bundle_pk, debug_jpeg=debug_jpeg)
        with transaction.atomic():
            ManagePageToImage.objects.create(
                bundle=bundle_obj,
                huey_id=task.id,
                status="queued",
                created=timezone.now(),
            )

    @transaction.atomic
    def get_bundle_split_completions(self, bundle_pk):
        bundle_obj = StagingBundle.objects.get(pk=bundle_pk)
        return ManagePageToImage.objects.get(bundle=bundle_obj).completed_pages

    @transaction.atomic
    def is_bundle_mid_splitting(self, bundle_pk):
        bundle_obj = StagingBundle.objects.get(pk=bundle_pk)
        if bundle_obj.has_page_images:
            return False

        query = ManagePageToImage.objects.filter(bundle=bundle_obj)
        if query.exists():  # have run a bundle-split task previously
            if query.exclude(
                status="completed"
            ).exists():  # one of these is not completed, so must be mid-run
                return True
            else:  # all have finished previously
                return False
        else:  # no such qr-reading tasks have been done
            return False

    @transaction.atomic
    def remove_bundle(self, bundle_name, *, user=None):
        """Remove a bundle PDF from the filesystem + database

        Args:
            bundle_name (str): which bundle.

        Keyword Args:
            user (None/str): also filter by user.
                TODO: user is *not* for permissions: looks like just
                a way to identify a bundle.
        """
        if user:
            bundle = StagingBundle.objects.get(
                user=user,
                slug=bundle_name,
            )
        else:
            bundle = StagingBundle.objects.get(slug=bundle_name)
        self._remove_bundle(bundle.pk)

    @transaction.atomic
    def _remove_bundle(self, bundle_pk):
        """Remove a bundle PDF from the filesystem + database

        Args:
            bundle_pk: the primary key for a particular bundle.
        """
        bundle = StagingBundle.objects.get(pk=bundle_pk)
        pathlib.Path(bundle.pdf_file.path).unlink()
        bundle.delete()

    @transaction.atomic
    def check_for_duplicate_hash(self, hash):
        """
        Check if a PDF has already been uploaded: return True if the hash
        already exists in the database.
        """
        return StagingBundle.objects.filter(pdf_hash=hash).exists()

    @transaction.atomic
    def get_bundle_from_timestamp(self, timestamp):
        return StagingBundle.objects.get(
            timestamp=timestamp,
        )

    @transaction.atomic
    def get_bundle(self, timestamp, user):
        """
        Get a bundle from the database. To uniquely identify a bundle, we need
        its timestamp and user
        """
        return StagingBundle.objects.get(
            user=user,
            timestamp=timestamp,
        )

    @transaction.atomic
    def get_image(self, timestamp, user, index):
        """
        Get an image from the database. To uniquely identify an image, we need a bundle
        (and a timestamp, and user) and a page index
        """
        bundle = self.get_bundle(timestamp, user)
        return StagingImage.objects.get(
            bundle=bundle,
            bundle_order=index,
        )

    @transaction.atomic
    def get_n_images(self, bundle):
        """
        Get the number of page images in a bundle by counting the number of
        StagingImages saved to the database
        """
        return StagingImage.objects.filter(bundle=bundle).count()

    @transaction.atomic
    def get_all_images(self, bundle):
        """
        Get all the page images in a bundle
        """

        return StagingImage.objects.filter(bundle=bundle)

    @transaction.atomic
    def get_user_bundles(self, user):
        """
        Return all of the staging bundles that a user uploaded
        """
        # bundles = StagingBundle.objects.filter(user=user, has_page_images=True)
        return list(StagingBundle.objects.filter(user=user))

    def parse_qr_code(self, list_qr_codes):
        """
        Parsing QR codes into list of dictionaries

        Args:
            list_qr_codes: (list) QR codes returned from QRextract() method as a dictionary

        Return:
            groupings: (dict) Set of data from raw-qr-strings
            {
                'NE': {
                    'page_type': 'plom_qr',
                    'page_info': {
                        'paper_id': 1,
                        'page_num': 3,
                        'version_num': 1,
                        'public_code': '93849',
                    }
                    'quadrant': '1',
                    'tpv': '00001003001',
                    'x_coord': 2204,
                    'y_coord': 279.5
                },
                'SW': {
                    'page_type': 'plom_qr',
                    'page_info': {
                        'paper_id': 1,
                        'page_num': 3,
                        'version_num': 1,
                        'public_code': '93849',
                }
                    'quadrant': '3',
                    'tpv': '00001003001',
                    'x_coord': 234,
                    'y_coord': 2909.5
                },
                'SE': {
                    'page_type': 'plom_qr',
                    'page_info': {
                        'paper_id': 1,
                        'page_num': 3,
                        'version_num': 1,
                        'public_code': '93849',
                    }
                    'quadrant': '4',
                    'tpv': '00001003001',
                    'x_coord': 2203,
                    'y_coord': 2906.5
                }
            }
            Alternatively, if the page is an extra page, then returns a similar dict but with entries of the form
                    'SE': {
                    'page_type': 'plom_extra',
                    'quadrant': '4',
                    'tpv': 'plomX',
                    'x_coord': 2203,
                    'y_coord': 2906.5
                }

        """
        # ++++++++++++++++++++++
        # TODO - hack this to handle tpv and plomX pages.
        # Need to add a tpv-utils method to decide if tpv or plomX and then
        # act accordingly here.
        # ++++++++++++++++++++++

        groupings = {}
        # TODO - simplify this loop using enumerate(list) or similar.
        for page in range(len(list_qr_codes)):
            for quadrant in list_qr_codes[page]:
                # note that from legacy-scan code the tpv_signature is the full raw "TTTTTPPPVVVOCCCCC" qr-string
                # while tpv refers to "TTTTTPPPVVV"
                raw_qr_string = list_qr_codes[page][quadrant].get("tpv_signature", None)
                if raw_qr_string is None:
                    continue
                x_coord = list_qr_codes[page][quadrant].get("x")
                y_coord = list_qr_codes[page][quadrant].get("y")
                qr_code_dict = {
                    "raw_qr_string": raw_qr_string,
                    "x_coord": x_coord,
                    "y_coord": y_coord,
                }

                if isValidTPV(raw_qr_string):
                    paper_id, page_num, version_num, public_code, corner = parseTPV(
                        raw_qr_string
                    )
                    tpv = getPaperPageVersion(
                        list_qr_codes[page][quadrant].get("tpv_signature")
                    )
                    qr_code_dict.update(
                        {
                            "page_type": "plom_qr",
                            "page_info": {
                                "paper_id": paper_id,
                                "page_num": page_num,
                                "version_num": version_num,
                                "public_code": public_code,
                            },
                            "quadrant": corner,
                            "tpv": tpv,
                        }
                    )
                elif isValidExtraPageCode(raw_qr_string):
                    corner = parseExtraPageCode(raw_qr_string)
                    qr_code_dict.update(
                        {
                            "page_type": "plom_extra",
                            "quadrant": corner,
                            "tpv": "plomX",
                        }
                    )
                groupings[quadrant] = qr_code_dict
        return groupings

    @transaction.atomic
    def read_qr_codes(self, bundle_pk):
        """
        Read QR codes of scanned pages in a bundle.
        QR Code:
        -         Test ID:  00001
        -        Page Num:  00#
        -     Version Num:  00#
        -              NW:  2
        -              NE:  1
        -              SW:  3
        -              SE:  4
        - Last five digit:  93849

        Args:
            bundle_pk: primary key of bundle DB object
        """
        root_folder = settings.MEDIA_ROOT / "page_images"
        root_folder.mkdir(exist_ok=True)

        bundle_obj = StagingBundle.objects.get(pk=bundle_pk)
        # check that the qr-codes have not been read already, or that a task has not been set

        if ManageParseQR.objects.filter(bundle=bundle_obj).exists():
            return

        task = huey_parent_read_qr_codes_task(bundle_pk)
        with transaction.atomic():
            ManageParseQR.objects.create(
                bundle=bundle_obj,
                huey_id=task.id,
                status="queued",
                created=timezone.now(),
            )

    def map_bundle_pages(self, bundle_pk, *, papernum, questions):
        """WIP support for hwscan.

        Args:
            bundle_pk: primary key of bundle DB object

        Keyword args:
            papernum (int):
            questions (list): doc elsewhere, but a list same length
                as the bundle, each element is list of which questions
                to attach that page too.
        """
        root_folder = settings.MEDIA_ROOT / "page_images"
        root_folder.mkdir(exist_ok=True)

        bundle_obj = StagingBundle.objects.get(pk=bundle_pk)

        # TODO: assert the length of question is same as pages in bundle

        print(bundle_obj)
        with transaction.atomic():
            # TODO: how do we walk them in order?
            for page_img, qlist in zip(
                bundle_obj.stagingimage_set.all().order_by("bundle_order"), questions
            ):
                print(page_img)
                print(page_img.rotation)
                print(page_img.parsed_qr)
                if not qlist:
                    page_img.image_type = "discard"
                    page_img.save()
                    DiscardStagingImage.objects.create(
                        staging_image=page_img, discard_reason="map said drop this page"
                    )
                    continue
                page_img.image_type = "extra"
                # TODO = update the qr-code info in the underlying image
                page_img.save()
                ExtraStagingImage.objects.create(
                    staging_image=page_img,
                    paper_number=papernum,
                    question_list=qlist,
                )
            # finally - mark the bundle as having had its qr-codes read.
            bundle_obj.has_qr_codes = True
            bundle_obj.save()

    def surgery_unknown_to_extra(self, bundle_pk, idx, *, papernum, questions):
        """Replace a single UnknownStagingImage with a ExtraStagingImage.

        This is to identify a completely blank paper.

        TODO: not sure ExtraStagingImage is the right thing.
        """
        raise NotImplementedError()

    @transaction.atomic()
    def surgery_map_extra(
        self, bundle_name, user_supplied_idx, *, papernum, question_list
    ):
        """Fill in the missing information in a ExtraStagingImage.

        This is to identify which paper and question(s) are in a ExtraStagingImage.
        You can call it again to update the information with new information.

        Args:
            bundle_name (str)
            user_supplied_idx (int): which page of the bundle to edit.
                Is 1-indexed.

        Keyword Args:
            papernum (int)
            question_list (list)

        Raises:
            ValueError: can't find things.

        TODO: some other routine for a page where all three QRcodes failed?
        """
        idx = user_supplied_idx  # internal bundle-order is 1-indexed

        bundle = StagingBundle.objects.get(slug=bundle_name)
        # note that this does not tell us if it is because the index is out of range
        # or if the page is not an extra-page, just that it does not exist
        try:
            ex_img = ExtraStagingImage.objects.get(
                staging_image__bundle=bundle, staging_image__bundle_order=idx
            )
        except ObjectDoesNotExist as e:
            raise ValueError(
                f"No extra page at index {user_supplied_idx} in "
                f'bundle "{bundle_name}": {e}'
            )

        if not Paper.objects.filter(paper_number=papernum).exists():
            raise ValueError(f"Paper {papernum} does not exist in the database")

        n_questions = SpecificationService().get_n_questions()
        sane_qlist = check_question_list(question_list, n_questions=n_questions)

        ex_img.paper_number = papernum
        ex_img.question_list = sane_qlist
        ex_img.save()

    @transaction.atomic
    def get_bundle_qr_completions(self, bundle_pk):
        bundle_obj = StagingBundle.objects.get(pk=bundle_pk)
        return ManageParseQR.objects.get(bundle=bundle_obj).completed_pages

    @transaction.atomic
    def is_bundle_mid_qr_read(self, bundle_pk):
        bundle_obj = StagingBundle.objects.get(pk=bundle_pk)
        if bundle_obj.has_qr_codes:
            return False

        query = ManageParseQR.objects.filter(bundle=bundle_obj)
        if query.exists():  # have run a qr-read task previously
            if query.exclude(
                status="completed"
            ).exists():  # one of these is not completed, so must be mid-run
                return True
            else:  # all have finished previously
                return False
        else:  # no such qr-reading tasks have been done
            return False

    @transaction.atomic
    def get_qr_code_results(self, bundle, page_index):
        """
        Check the results of a QR code scanning task. If done, return
        the QR code data. Otherwise, return None.
        """
        return StagingImage.objects.get(
            bundle=bundle, bundle_order=page_index
        ).parsed_qr

    def validate_qr_codes(self, bundle, spec):
        """
        Validate qr codes in bundle images (saved to disk) against the spec.
        """
        base_path = pathlib.Path(bundle.file_path).parent
        # print("SPEC PUBLIC CODE:", spec["publicCode"])
        qrs = checkQRsValid(base_path, spec)
        return qrs

    def get_n_pushed_images(self, bundle):
        """
        Return the number of staging images that have been pushed.
        """
        pushed = StagingImage.objects.filter(bundle=bundle, pushed=True)
        return len(pushed)

    @transaction.atomic
    def get_all_known_images(self, bundle):
        """
        Get all the images with completed QR code data - they can be pushed.
        """
        return list(bundle.stagingimage_set.filter(image_type="known"))

    @transaction.atomic
    def all_complete_images_pushed(self, bundle):
        """
        Return True if all of the completed images in a bundle have been pushed.
        """
        completed_images = self.get_all_complete_images(bundle)
        for img in completed_images:
            if not img.pushed:
                return False
        return True

    @transaction.atomic
    def get_n_pushed_bundles(self):
        pushed_bundles = StagingBundle.objects.filter(pushed=True)
        return len(pushed_bundles)

    @transaction.atomic
    def get_n_known_images(self, bundle):
        return bundle.stagingimage_set.filter(image_type="known").count()

    @transaction.atomic
    def get_n_unknown_images(self, bundle):
        return bundle.stagingimage_set.filter(image_type="unknown").count()

    @transaction.atomic
    def get_n_extra_images(self, bundle):
        return bundle.stagingimage_set.filter(image_type="extra").count()

    @transaction.atomic
    def get_n_extra_images_with_data(self, bundle):
        # note - we must check that we have set both questions and pages
        return bundle.stagingimage_set.filter(
            image_type="extra",
            extrastagingimage__paper_number__isnull=False,
            extrastagingimage__question_list__isnull=False,
        ).count()

    @transaction.atomic
    def do_all_extra_images_have_data(self, bundle):
        # Make sure all question pages have both paper-number and question-lists
        epages = bundle.stagingimage_set.filter(image_type="extra")
        return not epages.filter(
            Q(extrastagingimage__paper_number__isnull=True)
            | Q(extrastagingimage__question_list__isnull=True)
        ).exists()
        # if you can find an extra page with a null paper_number, or one with a null question-list then it is not ready.

    @transaction.atomic
    def get_n_error_images(self, bundle):
        return bundle.stagingimage_set.filter(image_type="error").count()

    @transaction.atomic
    def get_n_discard_images(self, bundle):
        return bundle.stagingimage_set.filter(image_type="discard").count()

    @transaction.atomic
    def bundle_contains_list(self, all_images, num_images):
        qr_code_list = []
        for image in all_images:
            for qr_quadrant in image.parsed_qr:
                qr_code_list.append(image.parsed_qr[qr_quadrant].get("grouping_key"))
        qr_code_list.sort()
        qr_code_list = list(dict.fromkeys(qr_code_list))
        while len(qr_code_list) < num_images:
            qr_code_list.append("unknown page")
        return qr_code_list

    @transaction.atomic
    def get_all_staging_image_hash(self):
        image_hash_list = StagingImage.objects.values("image_hash")
        return image_hash_list

    @transaction.atomic
    def staging_bundle_status_cmd(self):
        bundles = StagingBundle.objects.all()

        bundle_status = []
        status_header = (
            "Bundle name",
            "Id",
            "Total Pages",
            "Unknowns",
            "Knowns",
            "Extra (w data)",
            "Discards",
            "Error",
            "QR read",
            "Pushed",
            "Uploaded by",
        )
        bundle_status.append(status_header)
        for bundle in bundles:
            images = StagingImage.objects.filter(bundle=bundle)
            n_unknowns = self.get_n_unknown_images(bundle)
            n_knowns = self.get_n_known_images(bundle)
            n_extras_w_data = self.get_n_extra_images_with_data(bundle)
            n_discards = self.get_n_discard_images(bundle)
            n_errors = self.get_n_error_images(bundle)

            if self.is_bundle_mid_splitting(bundle.pk):
                count = ManagePageToImage.objects.get(bundle=bundle).completed_pages
                total_pages = f"in progress: {count} of {bundle.number_of_pages}"
            else:
                total_pages = images.count()

            bundle_qr_read = bundle.has_qr_codes
            if self.is_bundle_mid_qr_read(bundle.pk):
                count = ManageParseQR.objects.get(bundle=bundle).completed_pages
                bundle_qr_read = f"in progress ({count})"

            bundle_data = (
                bundle.slug,
                bundle.pk,
                total_pages,
                n_unknowns,
                n_knowns,
                n_extras_w_data,
                n_discards,
                n_errors,
                bundle_qr_read,
                bundle.pushed,
                bundle.user.username,
            )
            bundle_status.append(bundle_data)
        return bundle_status

    @transaction.atomic
    def read_bundle_qr_cmd(self, bundle_name):
        try:
            bundle_obj = StagingBundle.objects.get(slug=bundle_name)
        except ObjectDoesNotExist:
            raise ValueError(f"Bundle '{bundle_name}' does not exist!")

        if not bundle_obj.has_page_images:
            raise ValueError(f"Please wait for {bundle_name} to upload...")
        elif bundle_obj.has_qr_codes:
            raise ValueError(f"QR codes for {bundle_name} has been read.")
        self.read_qr_codes(bundle_obj.pk)

    @transaction.atomic
    def map_bundle_pages_cmd(self, bundle_name, *, papernum, questions=None):
        try:
            bundle_obj = StagingBundle.objects.get(slug=bundle_name)
        except ObjectDoesNotExist:
            raise ValueError(f"Bundle '{bundle_name}' does not exist!")

        if not bundle_obj.has_page_images:
            raise ValueError(f"Please wait for {bundle_name} to upload...")
        # elif bundle_obj.has_qr_codes:
        #    raise ValueError(f"QR codes for {bundle_name} has been read.")
        # TODO: ensure papernum exists, here or in the none-cmd?

        numpages = bundle_obj.number_of_pages
        print(f"DEBUG: numpages in bundle: {numpages}")
        numquestions = SpecificationService().get_n_questions()
        print(f"DEBUG: pre-canonical question:  {questions}")
        questions = canonicalize_page_question_map(questions, numpages, numquestions)
        print(f"DEBUG: canonical question list: {questions}")

        self.map_bundle_pages(bundle_obj.pk, papernum=papernum, questions=questions)

    @transaction.atomic
    def is_bundle_perfect(self, bundle_pk):
        """Tests if the bundle (given by its pk) is perfect. A bundle is perfect when
          * no unread pages, no error-pages, no unknown-pages, and
          * all extra pages have data.
        this, in turn, means that all pages present in bundle are
          * known or discard, or
          * are extra-pages with data
        """
        bundle_obj = StagingBundle.objects.get(pk=bundle_pk)
        # a bundle is perfect if it has

        # check for unread, unknown, error pages
        if bundle_obj.stagingimage_set.filter(
            image_type__in=["unknown", "unread", "error"]
        ).exists():
            return False
        # check for extra pages without data
        epages = bundle_obj.stagingimage_set.filter(image_type="extra")
        if epages.filter(
            Q(extrastagingimage__paper_number__isnull=True)
            | Q(extrastagingimage__question_list__isnull=True)
        ).exists():
            return False

        return True

    @transaction.atomic
    def push_bundle_to_server(self, bundle_obj):
        if bundle_obj.pushed:
            raise ValueError("Bundle has already been pushed. Cannot push again.")

        if not bundle_obj.has_qr_codes:
            raise ValueError("QR codes are not all read - cannot push bundle.")

        images = bundle_obj.stagingimage_set

        # make sure bundle is "perfect"
        # note function takes a bundle-pk as argument
        if not self.is_bundle_perfect(bundle_obj.pk):
            raise ValueError("The bundle is imperfect, cannot push.")

        img_service = ImageBundleService()

        # the bundle is valid so we can push it.
        try:
            img_service.upload_valid_bundle(bundle_obj)
            # now update the bundle and its images to say "pushed"
            bundle_obj.pushed = True
            bundle_obj.save()
            images.update(pushed=True)  # note that this also saves the objects.
        except RuntimeError as err:
            # todo - consider capturing this error in the future
            # so that we can display it to the user.
            raise err

    @transaction.atomic
    def push_bundle_cmd(self, bundle_name):
        try:
            bundle_obj = StagingBundle.objects.get(slug=bundle_name)
        except ObjectDoesNotExist:
            raise ValueError(f"Bundle '{bundle_name}' does not exist!")

        self.push_bundle_to_server(bundle_obj)

    @transaction.atomic
    def get_paper_id_and_page_num(self, image_qr):
        paper_id = []
        page_num = []
        for q in image_qr:
            paper_id.append(image_qr.get(q)["paper_id"])
            page_num.append(image_qr.get(q)["page_num"])

        return mode(paper_id), mode(page_num)

    @transaction.atomic
    def get_bundle_pages_info_list(self, bundle_obj):
        """Returns an of the pages within the given bundle ordered by
        their bundle-order.  Each item in the list is a dict
        containing the image-type, bundle-order, rotation, and info.
        The info value is itself a dict containing different items
        depending on the image-type. For error-pages and discard-pages
        it contains the "reason" while for known pages it contains
        paper_number, page_number and version. Finally for extra-pages
        it contains paper_number, and question_list.

        """

        # compute number of digits in longest page number to pad the page numbering
        n_digits = len(str(bundle_obj.number_of_pages))

        # We compute the list in two steps.
        # First we compute a dict of (key, value) (bundle_order, page_information)
        # Second we flatten that dict into an ordered list.

        # To do build the dict, we loop over all images and set up the
        # dict entries, and then loop over each separate image-type in
        # order to populate the information-field. This allows us to
        # prefetch the required information and so avoid any N+1 query
        # problems.
        pages = {}
        for img in bundle_obj.stagingimage_set.all().order_by("bundle_order"):
            pages[img.bundle_order] = {
                "status": img.image_type,
                "info": {},
                "order": f"{img.bundle_order}".zfill(n_digits),  # order is 1-indexed
                "rotation": img.rotation,
            }

        for img in bundle_obj.stagingimage_set.filter(
            image_type="error"
        ).prefetch_related("errorstagingimage"):
            pages[img.bundle_order]["info"] = {
                "reason": img.errorstagingimage.error_reason
            }

        for img in bundle_obj.stagingimage_set.filter(
            image_type="discard"
        ).prefetch_related("discardstagingimage"):
            pages[img.bundle_order]["info"] = {
                "reason": img.discardstagingimage.discard_reason
            }

        for img in bundle_obj.stagingimage_set.filter(
            image_type="known"
        ).prefetch_related("knownstagingimage"):
            pages[img.bundle_order]["info"] = {
                "paper_number": img.knownstagingimage.paper_number,
                "page_number": img.knownstagingimage.page_number,
                "version": img.knownstagingimage.version,
            }
        for img in bundle_obj.stagingimage_set.filter(
            image_type="extra"
        ).prefetch_related("extrastagingimage"):
            pages[img.bundle_order]["info"] = {
                "paper_number": img.extrastagingimage.paper_number,
                "question_list": img.extrastagingimage.question_list,
            }

        # now build an ordered list by running the keys (which are bundle-order) of the pages-dict in order.
        return [pages[ord] for ord in sorted(pages.keys())]

    @transaction.atomic
    def get_bundle_papers_pages_list(self, bundle_obj):
        """Returns an ordered list of papers and their known/extra
        pages in the given bundle.  Each item in the list is a pair
        (paper_number, page-info). The page-info is itself a ordered
        list of dicts. Each dict contains information about a page in
        the given paper in the given bundle.
        """

        # We build the ordered list in two steps. First build a dict of lists indexed by paper-number.
        papers = {}
        # Loop over the known-images first and then the extra-pages.
        for known in (
            KnownStagingImage.objects.filter(staging_image__bundle=bundle_obj)
            .order_by("paper_number", "page_number")
            .prefetch_related("staging_image")
        ):
            papers.setdefault(known.paper_number, []).append(
                {
                    "type": "known",
                    "page": known.page_number,
                    "order": known.staging_image.bundle_order,
                }
            )
        # Now loop over the extra pages
        for extra in (
            ExtraStagingImage.objects.filter(staging_image__bundle=bundle_obj)
            .order_by("paper_number", "question_list")
            .prefetch_related("staging_image")
        ):
            papers.setdefault(extra.paper_number, []).append(
                {
                    "type": "extra",
                    "question_list": extra.question_list,
                    "order": extra.staging_image.bundle_order,
                }
            )
        # # recast paper_pages as an **ordered** list of tuples (paper, page-info)
        return [(paper_number, page_info) for paper_number, page_info in sorted(papers.items())]

    @transaction.atomic
    def get_bundle_pages_info_cmd(self, bundle_name):
        try:
            bundle_obj = StagingBundle.objects.get(slug=bundle_name)
        except ObjectDoesNotExist:
            raise ValueError(f"Bundle '{bundle_name}' does not exist!")
        return self.get_bundle_pages_info_list(bundle_obj)

    @transaction.atomic
    def get_bundle_single_page_info(self, bundle_obj, index):
        # compute number of digits in longest page number to pad the page numbering
        n_digits = len(str(bundle_obj.number_of_pages))

        img = bundle_obj.stagingimage_set.get(bundle_order=index)
        current_page = {
            "status": img.image_type,
            "order": f"{img.bundle_order}".zfill(n_digits),  # order is 1-indexed
            "rotation": img.rotation,
            "qr_codes": img.parsed_qr,
        }
        if img.image_type == "error":
            info = {"reason": img.errorstagingimage.error_reason}
        elif img.image_type == "discard":
            info = {"reason": img.discardstagingimage.discard_reason}
        elif img.image_type == "known":
            info = {
                "paper_number": img.knownstagingimage.paper_number,
                "page_number": img.knownstagingimage.page_number,
                "version": img.knownstagingimage.version,
            }
        elif img.image_type == "extra":
            info = {
                "paper_number": img.extrastagingimage.paper_number,
                "question_list": img.extrastagingimage.question_list,
            }
        else:
            info = {}

        current_page.update({"info": info})
        return current_page


# ----------------------------------------
# factor out the huey tasks.
# ----------------------------------------


@db_task(queue="tasks")
def huey_parent_split_bundle_task(bundle_pk, *, debug_jpeg=False):
    from time import sleep

    bundle_obj = StagingBundle.objects.get(pk=bundle_pk)

    # note that we index bundle images from 1 not zero,
    with tempfile.TemporaryDirectory() as tmpdir:
        task_list = [
            huey_child_get_page_image(
                bundle_pk,
                pg,  # note pg is 1-indexed
                pathlib.Path(tmpdir),
                f"page{pg:05}",  # filename matches our 1-index
                quiet=True,
                debug_jpeg=debug_jpeg,
            )
            for pg in range(1, bundle_obj.number_of_pages + 1)
        ]

        # results = [X.get(blocking=True) for X in task_list]
        n_tasks = len(task_list)
        while True:
            results = [X.get() for X in task_list]
            count = sum(1 for X in results if X is not None)

            # TODO - check for error status here.

            with transaction.atomic():
                task_obj = ManagePageToImage.objects.get(bundle=bundle_obj)
                task_obj.completed_pages = count
                task_obj.save()

            if count == n_tasks:
                break
            else:
                sleep(1)

        with transaction.atomic():
            for X in results:
                with open(X["file_path"], "rb") as fh:
                    StagingImage.objects.create(
                        bundle=bundle_obj,
                        bundle_order=X["index"],
                        image_file=File(fh, name=X["file_name"]),
                        image_hash=X["image_hash"],
                    )

            bundle_obj.has_page_images = True
            bundle_obj.save()


@db_task(queue="tasks")
def huey_parent_read_qr_codes_task(bundle_pk):
    from time import sleep

    bundle_obj = StagingBundle.objects.get(pk=bundle_pk)

    task_list = [
        huey_child_parse_qr_code(page.pk, quiet=True)
        for page in bundle_obj.stagingimage_set.all()
    ]

    # results = [X.get(blocking=True) for X in task_list]

    n_tasks = len(task_list)
    while True:
        results = [X.get() for X in task_list]
        count = sum(1 for X in results if X is not None)

        with transaction.atomic():
            task_obj = ManageParseQR.objects.get(bundle=bundle_obj)
            task_obj.completed_pages = count
            task_obj.save()

        if count == n_tasks:
            break
        else:
            sleep(1)

    with transaction.atomic():
        for X in results:
            # TODO - check for error status here.
            img = StagingImage.objects.get(pk=X["image_pk"])
            img.parsed_qr = X["parsed_qr"]
            img.rotation = X["rotation"]
            img.save()

        bundle_obj.has_qr_codes = True
        bundle_obj.save()

    QRErrorService().check_read_qr_codes(bundle_obj)


@db_task(queue="tasks")
def huey_child_get_page_image(
    bundle_pk, index, basedir, basename, *, quiet=True, debug_jpeg=False
):
    """
    Render a page image and save to disk in the background

    Args:
        bundle_pk: bundle DB object's primary key
        index (int): bundle order of page - 1-indexed
        basedir (pathlib.Path): were to put the image
        basename (str): a basic filename without the extension

    Keyword Args:
        quiet (bool): currently unused?
        debug_jpeg (bool): off by default.  If True then we make some rotations by
            non-multiplies of 90, and save some low-quality jpegs.
    """
    bundle_obj = StagingBundle.objects.get(pk=bundle_pk)

    with fitz.open(bundle_obj.pdf_file.path) as pdf_doc:
        save_path = render_page_to_bitmap(
            pdf_doc[index - 1],  # PyMuPDF is 0-indexed
            basedir,
            basename,
            bundle_obj.pdf_file,
            add_metadata=True,
        )
    # For testing, randomly make jpegs, rotated a bit, of various qualities
    if debug_jpeg and random.uniform(0, 1) <= 0.5:
        _ = make_mucked_up_jpeg(save_path, basedir / ("muck-" + basename + ".jpg"))
        save_path.unlink()
        save_path = _
    with open(save_path, "rb") as f:
        image_hash = hashlib.sha256(f.read()).hexdigest()

    # TODO - return an error of some sort here if problems

    return {
        "index": index,
        "file_name": save_path.name,
        "file_path": str(save_path),
        "image_hash": image_hash,
    }


@db_task(queue="tasks")
def huey_child_parse_qr_code(image_pk, *, quiet=True):
    """
    Huey task of parsing QR codes, check QR errors, rotate image,
    and save to database in the background

    Args:
        image_pk: primary key of the image
    """
    img = StagingImage.objects.get(pk=image_pk)
    image_path = img.image_file.path

    scanner = ScanService()

    code_dict = QRextract(image_path)
    page_data = scanner.parse_qr_code([code_dict])

    pipr = PageImageProcessor()

    has_had_rotation = pipr.rotate_page_image(image_path, page_data)
    # Re-read QR codes if the page image has been rotated
    if has_had_rotation != 0:
        code_dict = QRextract(image_path)
        page_data = scanner.parse_qr_code([code_dict])
        # qr_error_checker.check_qr_codes(page_data, image_path, bundle)

    # Return the parsed QR codes for parent process to store in db
    # Zero rotation returned because rotate_page_image() modifies the image
    return {
        "image_pk": image_pk,
        "parsed_qr": page_data,
        "rotation": 0,
    }
