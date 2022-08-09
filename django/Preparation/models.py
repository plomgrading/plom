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


class PrenameClasslistCSV(SingletonBaseModel):
    # TODO - set a better upload path
    csv_file = models.FileField(upload_to="sources/")
    valid = models.BooleanField(default=False, null=False)
    warnings_errors_list = models.JSONField()


# ---------------------------------
# Make a table for students - this will likely be deprecated later


class PrenameStudent(models.Model):
    """Table to store information about students who have taken this
    assessment. Note, name is stored as a single field.

    student_id (str): The students id-number or id-string. Must be unique.
    student_name (str): The name of the student (as a single text field)
    paper_number (int): Optional paper_number assigned to this student. For
        prenaming - not linked to the actual DB for papers

    """

    # To understand why a single name-field, see
    # https://www.kalzumeus.com/2010/06/17/falsehoods-programmers-believe-about-names/

    # to allow for case where we know name but not id.
    student_id = models.TextField(null=True, unique=True)
    # must have unique id.
    student_name = models.TextField(null=False)
    # optional paper-number for prenaming
    paper_number = models.PositiveIntegerField(null=True)
