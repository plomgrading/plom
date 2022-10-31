from django.db import models

from Base.models import HueyTask
from Scan.models import StagingImage


class CreatePaperTask(HueyTask):
    """
    Create a test-paper and save its structure to the database.
    """

    paper_number = models.PositiveIntegerField(null=False, unique=True)


class CreateImageTask(HueyTask):
    """
    Create an image by copying a validated StagingImage instance.
    """

    staging_image = models.ForeignKey(
        StagingImage, null=True, on_delete=models.SET_NULL
    )
