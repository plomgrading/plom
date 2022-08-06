from django.db import models

# Create your models here.


class PaperSourcePDF(models.Model):
    version = models.PositiveIntegerField(unique=True)
    source_pdf = models.FileField(upload_to="sources/")
    hash = models.CharField(null=False, max_length=64)
