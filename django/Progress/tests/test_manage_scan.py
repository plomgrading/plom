from django.test import TestCase
from django.conf import settings
from model_bakery import baker

from Papers.models import (
    Image,
    CollidingImage,
    BasePage,
    DNMPage,
    DiscardedImage,
    Bundle,
)
from Scan.models import StagingImage, StagingBundle

from Progress.services import ManageScanService


class ManageScanTests(TestCase):
    """
    Tests for Progress.services.ManageScanService()
    """

    def setUp(self):
        self.bundle = baker.make(
            Bundle,
            hash="qwerty",
        )

        self.staged_image = baker.make(
            StagingImage,
            bundle=baker.make(StagingBundle, pdf_hash="qwerty"),
            bundle_order=1,
        )

        self.image = baker.make(
            Image,
            hash="lmnop",
            file_name=f"{settings.BASE_DIR}/media/page_images/test_papers/1/page1.png",
        )

        self.page = baker.make(
            DNMPage,
            image=self.image,
        )

        self.colliding_image = baker.make(
            CollidingImage,
            file_name=f"{settings.BASE_DIR}/media/page_images/colliding_pages/1/page1_abcdef.png",
            hash="abcdef",
            paper_number=1,
            page_number=1,
            bundle=self.bundle,
            bundle_order=1,
        )
        return super().setUp()

    def test_discarded_image_path(self):
        """
        Test ManageScanService.get_discarded_image_path()
        """

        mss = ManageScanService()
        new_path = mss.get_discarded_image_path("abcde", make_dirs=False)
        self.assertEqual(
            str(new_path),
            f"{settings.BASE_DIR}/media/page_images/discarded_pages/abcde.png",
        )

    def test_discard_colliding(self):
        """
        Test ManageScanService.discard_colliding_image()
        """

        mss = ManageScanService()
        mss.discard_colliding_image(self.colliding_image, make_dirs=False)
        discarded_image = DiscardedImage.objects.get(hash="abcdef")

        self.assertEqual(discarded_image.hash, "abcdef")
        self.assertEqual(
            discarded_image.file_name,
            f"{settings.BASE_DIR}/media/page_images/discarded_pages/abcdef.png",
        )

    def test_replace_image(self):
        """
        Test ManageScanService.replace_image_with_colliding()
        """

        mss = ManageScanService()
        mss.replace_image_with_colliding(
            self.image,
            self.colliding_image,
            make_dirs=False,
        )

        new_image = Image.objects.get(hash="abcdef")
        self.assertEqual(
            str(new_image.file_name),
            f"{settings.BASE_DIR}/media/page_images/test_papers/1/page1.png",
        )

        discarded = DiscardedImage.objects.get(hash="lmnop")
        self.assertEqual(
            str(discarded.file_name),
            f"{settings.BASE_DIR}/media/page_images/discarded_pages/lmnop.png",
        )
