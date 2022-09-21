from django.db import models

from Base.models import HueyTask


class CreatePaperTask(HueyTask):
    """
    Create a test-paper and save its structure to the database.
    """

    paper_number = models.PositiveIntegerField(null=False, unique=True)
