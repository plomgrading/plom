# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates

import shutil

from django.db import transaction
from django.conf import settings

from Papers.models import Bundle, Image


class ImageBundleService:
    """
    Class to encapsulate all functions around validated page images and bundles.
    """

    @transaction.atomic
    def create_bundle(self, name, hash):
        """
        Create a bundle and store its name and sha256 hash.
        """
        if Bundle.objects.filter(hash=hash).exists():
            raise RuntimeError("A bundle with that hash already exists.")
        bundle = Bundle(name=name, hash=hash)
        bundle.save()
        return bundle

    def get_bundle(self, hash):
        """
        Get a bundle from its hash.
        """
        return Bundle.objects.get(hash=hash)

    @transaction.atomic
    def create_image(
        self, bundle, bundle_order, original_name, file_name, hash, rotation
    ):
        """
        Create an image.
        """

        if Image.objects.filter(hash=hash).exists():
            raise RuntimeError("An image with that hash already exists.")
        image = Image(
            bundle=bundle,
            bundle_order=bundle_order,
            original_name=original_name,
            file_name=file_name,
            hash=hash,
            rotation=rotation,
        )
        image.save()
        return image

    @transaction.atomic
    def push_staged_image(self, staged_image, test_paper, page_number):
        """
        Save a staged bundle image to the database, after it has been
        successfully validated.

        Args:
            staged_image: StagingImage instance
            test_paper: string, test-paper ID of the image
            page_number: int, page number in the test (not the bundle)
        """

        staged_bundle = staged_image.bundle
        if not Bundle.objects.filter(hash=staged_bundle.pdf_hash).exists():
            bundle = self.create_bundle(staged_bundle.slug, staged_bundle.pdf_hash)
        else:
            bundle = self.get_bundle(staged_bundle.pdf_hash)

        file_path = self.get_page_image_path(test_paper, f"page{page_number}.png")

        image = self.create_image(
            bundle=bundle,
            bundle_order=staged_image.bundle_order,
            original_name=staged_image.file_name,
            file_name=file_path,
            hash=staged_image.image_hash,
            rotation=staged_image.rotation,
        )

        shutil.copy(staged_image.file_path, file_path)
        staged_image.pushed = True
        staged_image.save()
        return image

    def get_page_image_path(self, test_paper, file_name):
        """
        Return a save path for a test-paper page image.
        Also, create the necessary folders in the media directory
        if they don't exist.
        """
        page_image_dir = settings.BASE_DIR / "media" / "page_images"
        page_image_dir.mkdir(exist_ok=True)

        test_papers_dir = page_image_dir / "test_papers"
        test_papers_dir.mkdir(exist_ok=True)

        paper_dir = test_papers_dir / str(test_paper)
        paper_dir.mkdir(exist_ok=True)

        return str(paper_dir / file_name)

    def copy_image(self, staging_path, push_path):
        """
        Copy an image from media/{username} to media/page_images
        """

    def image_exists(self, hash):
        """
        Return True if a page image with the input hash exists in the database.
        """
        return Image.objects.filter(hash=hash).exists()
