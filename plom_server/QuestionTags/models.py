from django.db import models

class Question(models.Model):
    name = models.CharField(max_length=255)
    # other fields as necessary

    def __str__(self):
        return self.name
