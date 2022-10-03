import pathlib
import hashlib
from datetime import datetime
from django.db import transaction
from django.conf import settings

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
        bundle_dir = user_dir / "bundles"
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

        image_dir = user_dir / "images"
        image_dir.mkdir(exist_ok=True)
        slug_dir = image_dir / f"{slug}_{timestamp}"
        slug_dir.mkdir(exist_ok=True)
        self.split_and_save_bundle_images(pdf_doc, bundle_db, slug_dir)

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
        timestamp = datetime.timestamp(bundle.time_uploaded)
        for i in range(n_pages):
            filename = f"{bundle.slug}_{timestamp}_{i}.png"
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
        file_path = bundle.file_path
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
