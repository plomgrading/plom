from django.db import models


# Create your models here.
class Task(models.Model):
    paper_number = models.IntegerField()
    pdf_file = models.BinaryField(null=True, blank=True)
    status = models.CharField(max_length=20)
    created = models.DateTimeField(auto_now_add=True)
