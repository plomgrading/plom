# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2022 Brennen Chiu

import pathlib
import hashlib
import fitz
from datetime import datetime
from django.db import transaction
from django_huey import db_task
from plom.scan import QRextract
from plom.scan.readQRCodes import checkQRsValid

from .image_process import PageImageProcessor
from Scan.models import (
    StagingBundle,
    StagingImage,
    PageToImage,
    ParseQR,
)

from .qr_validators import QRErrorService


class ScanService:
    """
    Functions for staging scanned test-papers.
    """

    @transaction.atomic
    def upload_bundle(self, pdf_doc, slug, user, timestamp, pdf_hash):
        """
        Upload a bundle PDF and store it in the filesystem + database.
        Also, split PDF into page images + store in filesystem and database.
        """
        file_name = f"{timestamp}.pdf"

        user_dir = pathlib.Path("media") / user.username
        user_dir.mkdir(exist_ok=True)
        bundles_dir = user_dir / "bundles"
        bundles_dir.mkdir(exist_ok=True)
        bundle_dir = bundles_dir / f"{timestamp}"
        bundle_dir.mkdir(exist_ok=True)
        with open(bundle_dir / file_name, "w") as f:
            pdf_doc.save(f)

        bundle_db = StagingBundle(
            slug=slug,
            file_path=bundle_dir / file_name,
            user=user,
            timestamp=timestamp,
            pdf_hash=pdf_hash,
        )
        bundle_db.save()

        image_dir = bundle_dir / "pageImages"
        image_dir.mkdir(exist_ok=True)
        unknown_dir = bundle_dir / "unknownPages"
        unknown_dir.mkdir(exist_ok=True)
        self.split_and_save_bundle_images(pdf_doc, bundle_db, image_dir)

    @transaction.atomic
    def split_and_save_bundle_images(self, pdf_doc, bundle, base_dir):
        """
        Read a PDF document and save page images to filesystem/database

        Args:
            pdf_doc: fitz.document object of a bundle
            bundle: StagingBundle object
            base_dir: pathlib.Path object of path to save image files
        """
        n_pages = pdf_doc.page_count
        for i in range(n_pages):
            save_path = base_dir / f"page{i}.png"
            page_task = self._get_page_image(bundle, i, save_path)
            page_task_db = PageToImage(
                bundle=bundle,
                huey_id=page_task.id,
                status="queued",
                created=datetime.now(),
            )
            page_task_db.save()

    @db_task(queue="tasks")
    def _get_page_image(bundle, index, save_path):
        """
        Render a page image and save to disk in the background

        Args:
            bundle: bundle DB object
            index: bundle order of page
            pdf_page: fitz.Page object of a bundle page
            save_path: str or pathlib.Path object of image disk location
        """
        pdf_doc = fitz.Document(bundle.file_path)
        transform = fitz.Matrix(4, 4)
        pixmap = pdf_doc[index].get_pixmap(matrix=transform)
        pixmap.save(save_path)

        image_hash = hashlib.sha256(pixmap.tobytes()).hexdigest()
        image_db = StagingImage(
            bundle=bundle,
            bundle_order=index,
            file_name=f"page{index}.png",
            file_path=str(save_path),
            image_hash=image_hash,
        )
        image_db.save()

    @transaction.atomic
    def remove_bundle(self, timestamp, user):
        """
        Remove a bundle PDF from the filesystem + database
        """
        bundle = self.get_bundle(timestamp, user)
        file_path = pathlib.Path(bundle.file_path)
        file_path.unlink()
        bundle.delete()

    @transaction.atomic
    def check_for_duplicate_hash(self, hash):
        """
        Check if a PDF has already been uploaded: return True if the hash
        already exists in the database.
        """
        duplicate_hashes = StagingBundle.objects.filter(pdf_hash=hash)
        return len(duplicate_hashes) > 0

    @transaction.atomic
    def get_bundle(self, timestamp, user):
        """
        Get a bundle from the database. To uniquely identify a bundle, we need
        its timestamp and user
        """
        bundle = StagingBundle.objects.get(
            user=user,
            timestamp=timestamp,
        )
        return bundle

    @transaction.atomic
    def get_image(self, timestamp, user, index):
        """
        Get an image from the database. To uniquely identify an image, we need a bundle
        (and a timestamp, and user) and a page index
        """
        bundle = self.get_bundle(timestamp, user)
        image = StagingImage.objects.get(
            bundle=bundle,
            bundle_order=index,
        )
        return image

    @transaction.atomic
    def get_n_images(self, bundle):
        """
        Get the number of page images in a bundle by counting the number of
        StagingImages saved to the database
        """
        images = StagingImage.objects.filter(bundle=bundle)
        return len(images)

    @transaction.atomic
    def get_user_bundles(self, user):
        """
        Return all of the staging bundles that a user uploaded
        """
        bundles = StagingBundle.objects.filter(user=user, has_page_images=True)
        return list(bundles)

    @transaction.atomic
    def user_has_running_image_tasks(self, user):
        """
        Return True if user has a bundle with associated PageToImage tasks
        that aren't all completed
        """
        running_bundles = StagingBundle.objects.filter(user=user, has_page_images=False)
        return len(running_bundles) != 0

    @transaction.atomic
    def get_bundle_being_split(self, user):
        """
        Return the bundle that is currently being split into page images.
        If no bundles are being split in the background for a user, raise an ObjectNotFound
        error.
        """
        running_bundle = StagingBundle.objects.get(user=user, has_page_images=False)
        return running_bundle

    @transaction.atomic
    def page_splitting_cleanup(self, bundle):
        """
        After all of the page images have been successfully rendered, mark
        bundle as 'has_page_images'
        """
        bundle.has_page_images = True
        bundle.save()

    @transaction.atomic
    def get_n_page_rendering_tasks(self, bundle):
        """
        Return the total number of PageToImage tasks for a bundle
        """
        tasks = PageToImage.objects.filter(bundle=bundle)
        return len(tasks)

    @transaction.atomic
    def get_n_completed_page_rendering_tasks(self, bundle):
        """
        Return the number of completed PageToImage tasks for a bundle
        """
        completed = PageToImage.objects.filter(bundle=bundle, status="complete")
        return len(completed)

    def parse_qr_code(self, list_qr_codes):
        """
        Parsing QR codes into list of dictionaries
        """
        groupings = {}
        for page in range(len(list_qr_codes)):
            for quadrant in list_qr_codes[page]:
                if list_qr_codes[page][quadrant]:
                    paper_id = "".join(list_qr_codes[page][quadrant])[0:5]
                    page_num = "".join(list_qr_codes[page][quadrant])[5:8]
                    version_num = "".join(list_qr_codes[page][quadrant])[8:11]

                    # grouping_key = "-".join([paper_id, page_num, version_num])
                    qr_code_dict = {
                        "paper_id": paper_id,
                        "page_num": page_num,
                        "version_num": version_num,
                        "quadrant": "".join(list_qr_codes[page][quadrant])[11],
                        "public_code": "".join(list_qr_codes[page][quadrant])[12:],
                    }
                    groupings[quadrant] = qr_code_dict

        return groupings

    @db_task(queue="tasks")
    def _huey_parse_qr_code(image_path):
        """
        Parse QR codes and save to database in the background
        """
        scanner = ScanService()
        qr_error_checker = QRErrorService()
        code_dict = QRextract(image_path, write_to_file=False)
        page_data = scanner.parse_qr_code([code_dict])
        # error handling here
        qr_error_checker.check_qr_codes(page_data, image_path)

        pipr = PageImageProcessor()
        rotated = pipr.rotate_page_image(image_path, page_data)
        
        # Below is to write the parsed QR code to database.
        img = StagingImage.objects.get(file_path=image_path)
        img.parsed_qr = page_data
        if rotated:
            img.rotation = rotated
        img.save()

    @transaction.atomic
    def qr_codes_tasks(self, bundle, page_index, image_path):
        """
        Task of parsing QR codes.
        """
        qr_task = self._huey_parse_qr_code(image_path)
        qr_task_obj = ParseQR(
            bundle=bundle,
            page_index=page_index,
            file_path=image_path,
            huey_id=qr_task.id,
            status="queued",
        )
        qr_task_obj.save()

    def read_qr_codes(self, bundle):
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
        """
        imgs = StagingImage.objects.filter(bundle=bundle)
        for page in imgs:
            self.qr_codes_tasks(bundle, page.bundle_order, page.file_path)

    @transaction.atomic
    def get_qr_code_results(self, bundle, page_index):
        """
        Check the results of a QR code scanning task. If done, return
        the QR code data. Otherwise, return None.
        """
        image = StagingImage.objects.get(bundle=bundle, bundle_order=page_index)
        return image.parsed_qr

    @transaction.atomic
    def get_qr_code_reading_status(self, bundle, page_index):
        """
        Get the status of a QR code reading task. If it doesn't exist, return None.
        """
        try:
            task = ParseQR.objects.get(bundle=bundle, page_index=page_index)
            return task.status
        except ParseQR.DoesNotExist:
            return None

    @transaction.atomic
    def get_qr_code_error_message(self, bundle, page_index):
        """
        Get the error message of a QR code reading task.
        """
        task = ParseQR.objects.get(bundle=bundle, page_index=page_index)
        return task.message

    @transaction.atomic
    def is_bundle_reading_started(self, bundle):
        """
        Return True if there are at least one ParseQR tasks without the status 'todo'
        """
        bundle_tasks = ParseQR.objects.filter(bundle=bundle)
        non_todo_bundle_tasks = bundle_tasks.exclude(status="todo")

        return len(bundle_tasks) > 0 and len(non_todo_bundle_tasks) > 0

    @transaction.atomic
    def is_bundle_reading_ongoig(self, bundle):
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
        print(len(bundle_tasks))
        print(len(ended_tasks))
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
