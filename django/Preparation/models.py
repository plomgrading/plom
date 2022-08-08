from django.db import models

# Create your models here.


class PaperSourcePDF(models.Model):
    version = models.PositiveIntegerField(unique=True)
    source_pdf = models.FileField(upload_to="sources/")
    hash = models.CharField(null=False, max_length=64)


# ---------------------------------
# Define a singleton model as per
# https://steelkiwi.com/blog/practical-application-singleton-design-pattern/
#
# Then use this to define tables for PrenamingSetting and ClasslistCSV
# ---------------------------------


class SingletonBaseModel(models.Model):
    """We define a singleton models for the test-specification. This
    abstract model ensures that any derived models have at most a single
    row."""

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass

    @classmethod
    def load(cls):
        obj, created = cls.objects.get_or_create(pk=1)
        return obj


class PrenamingSetting(SingletonBaseModel):
    enabled = models.BooleanField(default=False, null=False)


class ClasslistCSV(SingletonBaseModel):
    # TODO - set a better upload path
    csv_file = models.FileField(upload_to="sources/")
    valid = models.BooleanField(default=False, null=False)
    warnings_errors_list = models.JSONField()
