# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2022 Brennen Chiu

from operator import index
import pathlib
import hashlib
import fitz
from datetime import datetime
from django.db import transaction
from django_huey import db_task
from plom.scan import QRextract
from plom.scan.readQRCodes import checkQRsValid
from collections import defaultdict

from Scan.models import (
    StagingBundle,
    StagingImage,
    PageToImage,
)


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

    @transaction.atomic
    def read_qr_codes(self, bundle):
        """
        Read QR codes of scanned pages in a bundle, save results to disk.
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
        images = StagingImage.objects.filter(bundle=bundle).order_by("bundle_order")
        qr_codes = []
        for img in images:
            file_path = img.file_path
            code_dict = QRextract(file_path, write_to_file=False)
            qr_codes.append(code_dict)
        return qr_codes

    def parse_qr_code(self, list_qr_codes):
        """
        Parsing QR codes into list of dictionaries
        """
        groupings = defaultdict(list)
        for indx in range(len(list_qr_codes)):
            for quadrant in list_qr_codes[indx]:
                if list_qr_codes[indx][quadrant]:
                    paper_id = "".join(list_qr_codes[indx][quadrant])[0:5]
                    page_num = "".join(list_qr_codes[indx][quadrant])[5:8]
                    version_num = "".join(list_qr_codes[indx][quadrant])[8:11]

                    grouping_key = "-".join([paper_id, page_num, version_num])
                    qr_code_dict = {
                        "paper_id": paper_id,
                        "page_num": page_num,
                        "version_num": version_num,
                        "quadrant": "".join(list_qr_codes[indx][quadrant])[11],
                        "public_code": "".join(list_qr_codes[indx][quadrant])[12:],
                    }
                    groupings[grouping_key].append(qr_code_dict)

        return [qr_code_dict for qr_code_dict in groupings.values()]

    def validate_qr_codes(self, bundle, spec):
        """
        Validate qr codes in bundle images (saved to disk) against the spec.
        """
        base_path = pathlib.Path(bundle.file_path).parent
        print("SPEC PUBLIC CODE:", spec["publicCode"])
        qrs = checkQRsValid(base_path, spec)
        return qrs
