# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2022-2023 Brennen Chiu
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2023 Colin B. Macdonald
# Copyright (C) 2023 Natalie Balashov

from collections import Counter
from statistics import mode

import hashlib
import pathlib
import shutil

import fitz
from django.conf import settings
from django.contrib.auth.models import User
from django.core.files import File
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django_huey import db_task
from django.utils import timezone

from plom.scan import QRextract
from plom.scan import render_page_to_bitmap
from plom.scan.readQRCodes import checkQRsValid
from plom.tpv_utils import parseTPV, getPaperPageVersion

from .image_process import PageImageProcessor
from Scan.models import (
    StagingBundle,
    StagingImage,
    PageToImage,
    ParseQR,
    DiscardedStagingImage,
    CollisionStagingImage,
    ManagePageToImage,
    ManageParseQR,
)
from Papers.models import ErrorImage
from Papers.services import ImageBundleService


class ScanService:
    """
    Functions for staging scanned test-papers.
    """

    def upload_bundle(
        self, uploaded_pdf_file, slug, user, timestamp, pdf_hash, number_of_pages
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

        """

        # make sure the path is created
        user_dir = pathlib.Path("media") / user.username
        user_dir.mkdir(exist_ok=True)
        bundles_dir = user_dir / "bundles"
        bundles_dir.mkdir(exist_ok=True)
        bundle_dir = bundles_dir / f"{timestamp}"
        bundle_dir.mkdir(exist_ok=True)

        fh = uploaded_pdf_file.open()
        with transaction.atomic():
            bundle_obj = StagingBundle.objects.create(
                slug=slug,
                pdf_file=File(fh, name=f"{timestamp}.pdf"),
                user=user,
                timestamp=timestamp,
                number_of_pages=number_of_pages,
                pdf_hash=pdf_hash,
            )

        image_dir = bundle_dir / "pageImages"
        image_dir.mkdir(exist_ok=True)
        unknown_dir = bundle_dir / "unknownPages"
        unknown_dir.mkdir(exist_ok=True)
        self.split_and_save_bundle_images(bundle_obj.pk, image_dir)

    @transaction.atomic
    def upload_bundle_cmd(
        self, pdf_file_path, slug, username, timestamp, hashed, number_of_pages
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
        )

    def split_and_save_bundle_images(self, bundle_pk, base_dir):
        """
        Read a PDF document and save page images to filesystem/database

        Args:
            bundle_pk: StagingBundle object primary key
            base_dir: pathlib.Path object of path to save image files
        """
        bundle_obj = StagingBundle.objects.get(pk=bundle_pk)
        task = self.split_bundle_parent_task(bundle_pk, base_dir)
        with transaction.atomic():
            ManagePageToImage.objects.create(
                bundle=bundle_obj,
                huey_id=task.id,
                status="queued",
                created=timezone.now(),
            )

    @db_task(queue="tasks")
    def split_bundle_parent_task(bundle_pk, base_dir):
        bundle_obj = StagingBundle.objects.get(pk=bundle_pk)
        task_list = [
            ScanService().child_get_page_image(bundle_pk, pg, base_dir, f"page{pg:05}")
            for pg in range(bundle_obj.number_of_pages)
        ]
        with transaction.atomic():
            for task in task_list:
                PageToImage.objects.create(
                    bundle=bundle_obj,
                    huey_id=task.id,
                    status="queued",
                    created=timezone.now(),
                )

        results = [X.get(blocking=True) for X in task_list]

        with transaction.atomic():
            for X in results:
                # TODO - check for error status here.
                StagingImage.objects.create(
                    bundle=bundle_obj,
                    bundle_order=X["index"],
                    file_name=X["file_name"],
                    file_path=X["file_path"],
                    image_hash=X["image_hash"],
                )

            bundle_obj.has_page_images = True
            bundle_obj.save()

    @db_task(queue="tasks")
    def child_get_page_image(bundle_pk, index, basedir, basename):
        """
        Render a page image and save to disk in the background

        Args:
            bundle_pk: bundle DB object's primary key
            index: bundle order of page
            basedir (pathlib.Path): were to put the image
            basename (str): a basic filename without the extension
        """
        bundle_obj = StagingBundle.objects.get(pk=bundle_pk)

        with fitz.open(bundle_obj.pdf_file.path) as pdf_doc:
            save_path = render_page_to_bitmap(
                pdf_doc[index],
                basedir,
                basename,
                bundle_obj.pdf_file,
                add_metadata=True,
            )
        # TODO: if demo, then do make_mucked_up_jpeg here

        with open(save_path, "rb") as f:
            image_hash = hashlib.sha256(f.read()).hexdigest()

        # TODO - return an error of some sort here if problems

        return {
            "index": index,
            "file_name": f"page{index}.png",
            "file_path": str(save_path),
            "image_hash": image_hash,
        }

    @transaction.atomic
    def remove_bundle(self, timestamp, user):
        """
        Remove a bundle PDF from the filesystem + database
        """
        bundle = self.get_bundle(timestamp, user)
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

    @transaction.atomic
    def user_has_running_image_tasks(self, user):
        """
        Return True if user has a bundle with associated PageToImage tasks
        that aren't all completed
        """
        return StagingBundle.objects.filter(user=user, has_page_images=False).exists()

    @transaction.atomic
    def get_n_page_rendering_tasks(self, bundle):
        """
        Return the total number of PageToImage tasks for a bundle
        """
        return PageToImage.objects.filter(bundle=bundle).count()

    @transaction.atomic
    def get_n_completed_page_rendering_tasks(self, bundle):
        """
        Return the number of completed PageToImage tasks for a bundle
        """
        return PageToImage.objects.filter(bundle=bundle, status="complete").count()

    def parse_qr_code(self, list_qr_codes):
        """
        Parsing QR codes into list of dictionaries

        Args:
            list_qr_codes: (list) QR codes returned from QRextract() method as a dictionary

        Return:
            groupings: (dict) Group of TPV signature
            {
                'NE': {
                    'paper_id': 1,
                    'page_num': 3,
                    'version_num': 1,
                    'quadrant': '1',
                    'public_code': '93849',
                    'grouping_key': '00001003001',
                    'x_coord': 2204,
                    'y_coord': 279.5
                },
                'SW': {
                    'paper_id': 1,
                    'page_num': 3,
                    'version_num': 1,
                    'quadrant': '3',
                    'public_code': '93849',
                    'grouping_key': '00001003001',
                    'x_coord': 234,
                    'y_coord': 2909.5
                },
                'SE': {
                    'paper_id': 1,
                    'page_num': 3,
                    'version_num': 1,
                    'quadrant': '4',
                    'public_code': '93849',
                    'grouping_key': '00001003001',
                    'x_coord': 2203,
                    'y_coord': 2906.5
                }
            }
        """
        groupings = {}
        for page in range(len(list_qr_codes)):
            for quadrant in list_qr_codes[page]:
                if list_qr_codes[page][quadrant].get("tpv_signature"):
                    paper_id, page_num, version_num, public_code, corner = parseTPV(
                        list_qr_codes[page][quadrant].get("tpv_signature")
                    )
                    grouping_key = getPaperPageVersion(
                        list_qr_codes[page][quadrant].get("tpv_signature")
                    )
                    x_coord = list_qr_codes[page][quadrant].get("x")
                    y_coord = list_qr_codes[page][quadrant].get("y")
                    qr_code_dict = {
                        "paper_id": paper_id,
                        "page_num": page_num,
                        "version_num": version_num,
                        "quadrant": corner,
                        "public_code": public_code,
                        "grouping_key": grouping_key,
                        "x_coord": x_coord,
                        "y_coord": y_coord,
                    }
                    groupings[quadrant] = qr_code_dict
        return groupings

    @db_task(queue="tasks")
    def child_parse_qr_code(image_pk):
        """
        Huey task of parsing QR codes, check QR errors, rotate image,
        and save to database in the background

        Args:
            image_pk: primary key of the image
        """
        img = StagingImage.objects.get(pk=image_pk)
        image_path = img.file_path

        scanner = ScanService()
        # qr_error_checker = QRErrorService()

        code_dict = QRextract(image_path)
        page_data = scanner.parse_qr_code([code_dict])

        pipr = PageImageProcessor()
        has_had_rotation = pipr.rotate_page_image(image_path, page_data)
        # Re-read QR codes if the page image has been rotated
        if has_had_rotation != 0:
            code_dict = QRextract(image_path)
            page_data = scanner.parse_qr_code([code_dict])
            # qr_error_checker.check_qr_codes(page_data, image_path, bundle)

        # Return the parsed QR codes and rotation done for parent process to store in db
        return {"image_pk": image_pk, "parsed_qr": page_data, "rotation": has_had_rotation}

    @db_task(queue="tasks")
    def read_qr_codes_parent_task(bundle_pk):
        bundle_obj = StagingBundle.objects.get(pk=bundle_pk)

        # TODO - replace this by a foreign-key lookup thingy rather than another filter
        # the_pages = StagingImage.objects.filter(bundle=bundle_obj)
        arg_list = [
            (
                page.bundle_order,
                page.file_path,
                ScanService().child_parse_qr_code(page.pk),
            )
            for page in bundle_obj.stagingimage_set.all()
        ]

        with transaction.atomic():
            for X in arg_list:
                ParseQR.objects.create(
                    bundle=bundle_obj,
                    page_index=X[0],
                    file_path=X[1],
                    huey_id=X[2].id,
                    status="queued",
                )

        results = [X[2].get(blocking=True) for X in arg_list]

        with transaction.atomic():
            for X in results:
                # TODO - check for error status here.
                img = StagingImage.objects.get(pk=X["image_pk"])
                img.parsed_qr = X["parsed_qr"]
                img.rotation = X["rotation"]
                img.save()

            bundle_obj.has_qr_codes = True
            bundle_obj.save()

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

        task = self.read_qr_codes_parent_task(bundle_pk)
        with transaction.atomic():
            ManageParseQR.objects.create(
                bundle=bundle_obj,
                huey_id=task.id,
                status="queued",
                created=timezone.now(),
            )

    @transaction.atomic
    def is_bundle_mid_qr_read(self, bundle_pk):
        bundle_obj = StagingBundle.objects.get(pk=bundle_pk)
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

    @transaction.atomic
    def get_qr_code_reading_status(self, bundle, page_index):
        """
        Get the status of a QR code reading task. If it doesn't exist, return None.
        """
        try:
            return ParseQR.objects.get(bundle=bundle, page_index=page_index).status
        except ParseQR.DoesNotExist:
            return None

    @transaction.atomic
    def get_qr_code_error_message(self, bundle, page_index):
        """
        Get the error message of a QR code reading task.
        """
        return ParseQR.objects.get(bundle=bundle, page_index=page_index).message

    @transaction.atomic
    def is_bundle_reading_started(self, bundle):
        """
        Return True if there are at least one ParseQR tasks without the status 'todo'
        """
        bundle_tasks = ParseQR.objects.filter(bundle=bundle)
        return bundle_tasks.exists() and bundle_tasks.exclude(status="todo").exists()

    @transaction.atomic
    def is_bundle_reading_ongoing(self, bundle):
        """
        Return True if there are at least one ParseQR tasks without the status 'todo',
        'complete', or 'error'.
        """
        bundle_tasks = ParseQR.objects.filter(bundle=bundle)
        ongoing_tasks = bundle_tasks.filter(status="queued") | bundle_tasks.filter(
            status="started"
        )
        return len(bundle_tasks) > 0 and len(ongoing_tasks) > 0

    @transaction.atomic
    def is_bundle_reading_finished(self, bundle):
        """
        Return True if there is at least one ParseQR task and all statuses are 'complete'
        or 'error'.
        """
        bundle_tasks = ParseQR.objects.filter(bundle=bundle)
        ended_tasks = bundle_tasks.filter(status="error") | bundle_tasks.filter(
            status="complete"
        )
        return len(bundle_tasks) > 0 and len(bundle_tasks) == len(ended_tasks)

    @transaction.atomic
    def get_n_complete_reading_tasks(self, bundle):
        """
        Return the number of ParseQR tasks with the status 'complete'
        """
        complete_tasks = ParseQR.objects.filter(bundle=bundle, status="complete")
        return len(complete_tasks)

    @transaction.atomic
    def clear_qr_tasks(self, bundle):
        """
        Remove all of the ParseQR tasks for this bundle.
        """
        bundle_tasks = ParseQR.objects.filter(bundle=bundle)
        bundle_tasks.delete()

    @transaction.atomic
    def qr_reading_cleanup(self, bundle):
        """
        Mark bundle as having QR codes in the database.
        """
        bundle.has_qr_codes = True
        bundle.save()

    def validate_qr_codes(self, bundle, spec):
        """
        Validate qr codes in bundle images (saved to disk) against the spec.
        """
        base_path = pathlib.Path(bundle.file_path).parent
        print("SPEC PUBLIC CODE:", spec["publicCode"])
        qrs = checkQRsValid(base_path, spec)
        return qrs

    def get_n_pushed_images(self, bundle):
        """
        Return the number of staging images that have been pushed.
        """
        pushed = StagingImage.objects.filter(bundle=bundle, pushed=True)
        return len(pushed)

    @transaction.atomic
    def get_all_complete_images(self, bundle):
        """
        Get all the images with completed QR code data - they can be pushed.
        """
        complete = (
            StagingImage.objects.filter(bundle=bundle)
            .exclude(parsed_qr={})
            .exclude(pushed=True)
            .exclude(colliding=True)
            .exclude(error=True)
            .exclude(unknown=True)
        )
        return list(complete)

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
    def push_bundle(self, bundle):
        bundle.pushed = True
        bundle.save()

    @transaction.atomic
    def get_n_pushed_bundles(self):
        pushed_bundles = StagingBundle.objects.filter(pushed=True)
        return len(pushed_bundles)

    @transaction.atomic
    def get_error_image(self, bundle, index):
        error_image = ErrorImage.objects.get(
            bundle=bundle,
            bundle_order=index,
        )
        return error_image

    @transaction.atomic
    def get_n_error_image(self, bundle):
        error_images = StagingImage.objects.filter(bundle=bundle, error=True)
        return len(error_images)

    @transaction.atomic
    def get_n_flagged_image(self, bundle):
        flag_images = StagingImage.objects.filter(bundle=bundle, flagged=True)
        return len(flag_images)

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
    def get_common_qr_code(self, qr_data):
        qr_code_list = []
        for qr_quadrant in qr_data:
            paper_id = list(qr_data[qr_quadrant].values())[0]
            page_num = list(qr_data[qr_quadrant].values())[1]
            version_num = list(qr_data[qr_quadrant].values())[2]
            qr_code_list.append(paper_id + page_num + version_num)
        counter = Counter(qr_code_list)
        most_common_qr = counter.most_common(1)
        common_qr = most_common_qr[0][0]
        return common_qr

    @transaction.atomic
    def change_error_image_state(self, bundle, page_index, img_bundle):
        task = ParseQR.objects.get(bundle=bundle, page_index=page_index)
        task.status = "complete"
        task.save()
        error_image = self.get_error_image(img_bundle, page_index)
        error_image.delete()

    @transaction.atomic
    def get_all_staging_image_hash(self):
        image_hash_list = StagingImage.objects.values("image_hash")
        return image_hash_list

    @transaction.atomic
    def upload_replace_page(
        self, user, timestamp, time_uploaded, pdf_doc, index, uploaded_image_hash
    ):
        replace_pages_dir = (
            pathlib.Path("media")
            / user.username
            / "bundles"
            / str(timestamp)
            / "replacePages"
        )
        replace_pages_dir.mkdir(exist_ok=True)
        replace_pages_pdf_dir = replace_pages_dir / "pdfs"
        replace_pages_pdf_dir.mkdir(exist_ok=True)

        filename = f"{time_uploaded}.pdf"
        with open(replace_pages_pdf_dir / filename, "w") as f:
            pdf_doc.save(f)

        save_as_image_path = self.save_replace_page_as_image(
            replace_pages_dir, replace_pages_pdf_dir, filename, uploaded_image_hash
        )
        self.replace_image(
            user, timestamp, index, save_as_image_path, uploaded_image_hash
        )

    @transaction.atomic
    def save_replace_page_as_image(
        self,
        replace_pages_file_path,
        replace_pages_pdf_file_path,
        filename,
        uploaded_image_hash,
    ):
        save_replace_image_dir = replace_pages_file_path / "images"
        save_replace_image_dir.mkdir(exist_ok=True)
        save_as_image = save_replace_image_dir / f"{uploaded_image_hash}.png"

        upload_pdf_file = fitz.Document(replace_pages_pdf_file_path / filename)
        transform = fitz.Matrix(4, 4)
        pixmap = upload_pdf_file[0].get_pixmap(matrix=transform)
        pixmap.save(save_as_image)

        return save_as_image

    @transaction.atomic
    def replace_image(
        self, user, bundle_timestamp, index, saved_image_path, uploaded_image_hash
    ):
        # send the error image to discarded_pages folder
        root_folder = pathlib.Path("media") / "page_images" / "discarded_pages"
        root_folder.mkdir(exist_ok=True)

        error_image = self.get_image(bundle_timestamp, user, index)
        shutil.move(
            error_image.file_path, root_folder / f"{error_image.image_hash}.png"
        )

        discarded_image = DiscardedStagingImage(
            bundle=error_image.bundle,
            bundle_order=error_image.bundle_order,
            file_name=error_image.file_name,
            file_path=root_folder / f"{error_image.image_hash}.png",
            image_hash=error_image.image_hash,
            parsed_qr=error_image.parsed_qr,
            rotation=error_image.rotation,
            restore_class="replace",
        )
        discarded_image.save()

        error_image.file_path = saved_image_path
        error_image.image_hash = uploaded_image_hash
        error_image.save()

    @transaction.atomic
    def get_collision_image(self, bundle, index):
        collision_image = CollisionStagingImage.objects.get(
            bundle=bundle, bundle_order=index
        )
        return collision_image

    @transaction.atomic
    def change_collision_image_state(self, bundle, page_index):
        task = ParseQR.objects.get(bundle=bundle, page_index=page_index)
        task.status = "complete"
        task.save()
        staging_image = StagingImage.objects.get(bundle=bundle, bundle_order=page_index)
        staging_image.colliding = False
        staging_image.save()
        collision_image_obj = self.get_collision_image(bundle, page_index)
        collision_image_obj.delete()

    @transaction.atomic
    def discard_collision_image(self, bundle_obj, user, bundle_timestamp, page_index):
        root_folder = pathlib.Path("media") / "page_images" / "discarded_pages"
        root_folder.mkdir(exist_ok=True)

        collision_image = self.get_image(bundle_timestamp, user, page_index)
        shutil.move(
            collision_image.file_path, root_folder / f"{collision_image.image_hash}.png"
        )
        discarded_image = DiscardedStagingImage(
            bundle=collision_image.bundle,
            bundle_order=collision_image.bundle_order,
            file_name=collision_image.file_name,
            file_path=root_folder / f"{collision_image.image_hash}.png",
            image_hash=collision_image.image_hash,
            parsed_qr=collision_image.parsed_qr,
            rotation=collision_image.rotation,
            restore_class="collision",
        )
        discarded_image.save()

        bundle_order = collision_image.bundle_order
        collision_image.delete()

        parse_qr = ParseQR.objects.get(bundle=bundle_obj, page_index=bundle_order)
        parse_qr.delete()

        staging_image_list = StagingImage.objects.all()
        for staging_img_obj in staging_image_list[bundle_order:]:
            staging_img_obj.bundle_order -= 1
            staging_img_obj.save()

        parse_qr_list = ParseQR.objects.all()
        for parse_qr_obj in parse_qr_list[bundle_order:]:
            parse_qr_obj.page_index -= 1
            parse_qr_obj.save()

    @transaction.atomic
    def staging_bundle_status_cmd(self):
        bundles = StagingBundle.objects.all()
        img_service = ImageBundleService()
        scanner = ScanService()

        bundle_status = []
        status_header = (
            "Bundle name",
            "Total pages",
            "Valid pages",
            "Error pages",
            "QR read",
            "Pushed",
            "Uploaded by",
        )
        bundle_status.append(status_header)
        for bundle in bundles:
            images = StagingImage.objects.filter(bundle=bundle)
            valid_images = self.get_n_complete_reading_tasks(bundle)
            all_images = StagingImage.objects.filter(bundle=bundle)

            error_image_list = []
            for image in all_images:
                if image.colliding or image.error or image.unknown:
                    error_image_list.append(image)
            error_images = len(error_image_list)

            completed_images = scanner.get_all_complete_images(bundle)

            if len(images) == self.get_n_page_rendering_tasks(bundle):
                total_pages = len(images)
            else:
                total_pages = f"in progress - {len(images)}"

            reading_qr = self.is_bundle_reading_ongoing(bundle)
            bundle_qr_read = bundle.has_qr_codes
            if reading_qr:
                bundle_qr_read = "in progress"

            pushing_image = img_service.is_image_pushing_in_progress(completed_images)
            bundle_pushed = bundle.pushed
            if pushing_image:
                bundle_pushed = "in progress"

            bundle_data = (
                bundle.slug,
                total_pages,
                valid_images,
                error_images,
                bundle_qr_read,
                bundle_pushed,
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

        if self.get_n_completed_page_rendering_tasks(
            bundle_obj
        ) != self.get_n_page_rendering_tasks(bundle_obj):
            raise ValueError(f"Please wait for {bundle_name} to upload...")
        elif bundle_obj.has_qr_codes:
            raise ValueError(f"QR codes for {bundle_name} has been read.")
        else:
            self.read_qr_codes(bundle_obj.pk)

    @transaction.atomic
    def push_bundle_cmd(self, bundle_name):
        img_service = ImageBundleService()

        try:
            bundle_obj = StagingBundle.objects.get(slug=bundle_name)
        except ObjectDoesNotExist:
            raise ValueError(f"Bundle '{bundle_name}' does not exist!")

        images = StagingImage.objects.filter(bundle=bundle_obj)
        all_complete_images_objs = self.get_all_complete_images(bundle_obj)
        all_images = StagingImage.objects.filter(bundle=bundle_obj)
        error_image_list = []
        for image in all_images:
            if image.colliding or image.error or image.unknown:
                error_image_list.append(image)
        error_images = len(error_image_list)

        if not bundle_obj.has_qr_codes or self.is_bundle_reading_ongoig(bundle_obj):
            raise ValueError(
                f"Bundle '{bundle_name}' QR codes reading in progress or has not been read yet."
            )
        elif img_service.is_image_pushing_in_progress(all_complete_images_objs):
            raise ValueError(f"{bundle_name} pushing in progress...")
        elif bundle_obj.pushed:
            raise ValueError(f"Bundle '{bundle_name}' already pushed.")
        elif (len(all_complete_images_objs) != len(images)) or error_images > 0:
            raise ValueError(
                f"Please fix all the errors in Bundle '{bundle_name}' before pushing."
            )
        else:
            self.push_bundle(bundle_obj)
            for complete_image in all_complete_images_objs:
                paper_id, page_num = self.get_paper_id_and_page_num(
                    complete_image.parsed_qr
                )
                img_service.push_staged_image(complete_image, paper_id, page_num)

    @transaction.atomic
    def get_paper_id_and_page_num(self, image_qr):
        paper_id = []
        page_num = []
        for q in image_qr:
            paper_id.append(image_qr.get(q)["paper_id"])
            page_num.append(image_qr.get(q)["page_num"])

        return mode(paper_id), mode(page_num)
