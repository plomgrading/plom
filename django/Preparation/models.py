from django.db import models

# Create your models here.


class SourcePDF(models.Model):
    version = models.PositiveIntegerField(unique=True)
    pdf = models.FileField()
    hash = models.CharField(null=False, max_length=64)
