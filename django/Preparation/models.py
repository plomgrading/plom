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

    
class StagingClasslistCSV(SingletonBaseModel):
    """A temporary holder for the classlist csv for the purposes of preparing things."""
    # TODO - set a better upload path
    csv_file = models.FileField(upload_to="sources/")
    valid = models.BooleanField(default=False, null=False)
    warnings_errors_list = models.JSONField()


# ---------------------------------
# Make a table for students - for the purposes of preparing things. Hence "staging" prefix.


class StagingStudent(models.Model):
    """Table to store information about students for the purposes of
    preparing things for potential prenaming. Note, name is stored as a
    single field.

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


class StagingPQVMapping(models.Model):
    """Table to store the test-question-version mapping for staging.
    Store as triples of paper-question-version. This is very loose,
    but avoids recreating the entire paper-structure.

    """
    
    paper_number = models.PositiveIntegerField(null=False)
    question = models.PositiveIntegerField(null=False)
    version = models.PositiveIntegerField(null=False)


# ---------------------------------
# Make a table for info to help connect to the plom-classic server

class ClassicPlomServerInformation(SingletonBaseModel):
    server_name = models.TextField(default="localhost")
    server_port = models.PositiveIntegerField(default="41984")
    classic_server_manager_password = models.TextField(default="CHANGEME")
    # use these to show that we've pinged the server and checked the password
    server_validated = models.BooleanField(default=False, null=False)
    password_validated = models.BooleanField(default=False, null=False)
    
