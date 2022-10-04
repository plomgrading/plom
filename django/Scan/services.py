import pathlib
import hashlib
from datetime import datetime
from django.db import transaction
from django.conf import settings
from plom.scan import QRextract
from plom.scan.readQRCodes import checkQRsValid

from Scan.models import StagingBundle, StagingImage


class ScanService:
    """
    Functions for staging scanned test-papers.
    """

    @transaction.atomic
    def upload_bundle(self, pdf_doc, slug, user, time_uploaded, pdf_hash):
        """
        Upload a bundle PDF and store it in the filesystem + database.
        Also, split PDF into page images + store in filesystem and database.
        """
        timestamp = datetime.timestamp(time_uploaded)
        file_name = f"{slug}_{timestamp}.pdf"

        user_dir = pathlib.Path("media") / user.username
        user_dir.mkdir(exist_ok=True)
        bundles_dir = user_dir / "bundles"
        bundles_dir.mkdir(exist_ok=True)
        bundle_dir = bundles_dir / f"{slug}_{timestamp}"
        bundle_dir.mkdir(exist_ok=True)
        with open(bundle_dir / file_name, "w") as f:
            pdf_doc.save(f)

        bundle_db = StagingBundle(
            slug=slug,
            file_path=bundle_dir / file_name,
            user=user,
            time_uploaded=time_uploaded,
            pdf_hash=pdf_hash,
        )
        bundle_db.save()

        image_dir = bundle_dir / "pageImages"
        image_dir.mkdir(exist_ok=True)
        unknown_dir = bundle_dir / "unknownPages"
        unknown_dir.mkdir(exist_ok=True)
        self.split_and_save_bundle_images(pdf_doc, bundle_db, image_dir)

    @transaction.atomic
    def split_and_save_bundle_images(self, pdf_doc, bundle, save_path):
        """
        Read a PDF document and save page images to filesystem/database

        Args:
            pdf_doc: fitz.document object of a bundle
            bundle: StagingBundle object
            save_path: pathlib.Path object of path to save image files
        """
        n_pages = pdf_doc.page_count
        for i in range(n_pages):
            filename = f"page{i}.png"
            pixmap = pdf_doc.get_page_pixmap(i)
            pixmap.save(save_path / filename)

            with open(save_path / filename, "rb") as f:
                image_hash = hashlib.sha256(f.read()).hexdigest()

            image_db = StagingImage(
                bundle=bundle,
                bundle_order=i,
                file_name=filename,
                file_path=str(save_path / filename),
                image_hash=image_hash,
            )
            image_db.save()

    @transaction.atomic
    def remove_bundle(self, slug, timestamp, user):
        """
        Remove a bundle PDF from the filesystem + database
        """
        bundle = self.get_bundle(slug, timestamp, user)
        file_path = pathlib.Path(bundle.file_path)
        file_path.unlink()
        bundle.delete()

    @transaction.atomic
    def get_bundle(self, slug, timestamp, user):
        """
        Get a bundle from the database. To uniquely identify a bundle, we need
        its slug, timestamp, and user
        """
        time_uploaded = datetime.fromtimestamp(timestamp)
        bundle = StagingBundle.objects.get(
            slug=slug,
            user=user,
            time_uploaded=time_uploaded,
        )
        return bundle

    @transaction.atomic
    def get_image(self, slug, timestamp, user, index):
        """
        Get an image from the database. To uniquely identify an image, we need a bundle
        (and a slug, timestamp, and user) and a page index
        """
        bundle = self.get_bundle(slug, timestamp, user)
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
        bundles = StagingBundle.objects.filter(user=user)
        return list(bundles)

    @transaction.atomic
    def read_qr_codes(self, bundle):
        """
        Read QR codes of scanned pages in a bundle, save results on disk.
        """
        images = StagingImage.objects.filter(bundle=bundle).order_by("bundle_order")
        qr_codes = []
        for img in images:
            file_path = img.file_path
            code_dict = QRextract(file_path, write_to_file=False)
            qr_codes.append(code_dict)
        return qr_codes

    def validate_qr_codes(self, bundle, spec):
        """
        Validate qr codes in bundle images (saved to disk) against the spec.
        """
        base_path = pathlib.Path(bundle.file_path).parent
        print('SPEC PUBLIC CODE:', spec["publicCode"])
        qrs = checkQRsValid(base_path, spec)
        return qrs
