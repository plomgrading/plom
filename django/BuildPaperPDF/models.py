from datetime import datetime

from django.db import models


# Create your models here.
class Task(models.Model):
    paper_number = models.IntegerField()
    huey_id = models.UUIDField(null=True)
    pdf_file_path = models.TextField(default="")
    status = models.CharField(max_length=20)
    created = models.DateTimeField(default=datetime.now, blank=True)

    def __str__(self):
        return "Task Object " + str(self.paper_number)
