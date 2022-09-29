import pathlib
from datetime import datetime
from django.db import transaction
from django.conf import settings

from Scan.models import StagingBundle


class ScanService:
    """
    Functions for staging scanned test-papers.
    """

    @transaction.atomic
    def upload_bundle(self, pdf_doc, slug, user, time_uploaded, pdf_hash):
        """
        Upload a bundle PDF and store it in the filesystem + database
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
