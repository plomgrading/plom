import shutil
import re
import pathlib
from django.db import models
from django.db.models.signals import pre_delete
from django.utils.text import slugify

"""
TODO: move util functions outside models file, clean up old functions
"""

# just a simple folder for media for now
def temp_filename_path(instance, filename):
    slug = slugify(re.sub('.pdf$', '', filename))
    return pathlib.Path('TestCreator') / 'media' / f'{slug}.pdf'

class ReferencePDF(models.Model):
    # TODO: use TextField instead of CharField, don't hardcode field lengths!
    filename_slug = models.TextField(default='')
    pdf = models.FileField(upload_to=temp_filename_path)
    num_pages = models.IntegerField(default=0)

def pre_delete_reference_pdf(sender, instance, **kwargs):
    # delete thumbnails
    thumbnail_folder = pathlib.Path('TestCreator') / 'static' / 'thumbnails' / instance.filename_slug
    if thumbnail_folder.exists():
        shutil.rmtree(thumbnail_folder)

    # delete pdf from disk
    pdf_path = pathlib.Path('TestCreator') / 'media' / f'{instance.filename_slug}.pdf'
    pdf_path.unlink(missing_ok=True)

pre_delete.connect(
    pre_delete_reference_pdf, sender=ReferencePDF
)


class TestSpecInfo(models.Model):
    long_name = models.TextField()
    short_name = models.TextField()
    n_versions = models.PositiveIntegerField(default=0)
    n_to_produce = models.PositiveIntegerField(default=0)
    n_questions = models.IntegerField(default=0)
    total_marks = models.IntegerField(default=0)
    pages = models.JSONField(default=dict)


SHUFFLE_CHOICES = (
    ('S', "Shuffle"),
    ('F', "Fix")
)


# TODO: enforce field lengths in the form, not the database?
class TestSpecQuestion(models.Model):
    index = models.PositiveIntegerField(default=1)
    label = models.TextField()
    mark = models.PositiveIntegerField(default=0)
    shuffle = models.CharField(choices=SHUFFLE_CHOICES, max_length=100)


class TestSpecProgress(models.Model):
    is_names_completed = models.BooleanField(default=False)
    is_versions_pdf_completed = models.BooleanField(default=False)
    is_id_page_completed = models.BooleanField(default=False)
    is_question_page_completed = models.BooleanField(default=False)
    are_questions_completed = models.JSONField(default=dict)
    are_pages_selected = models.JSONField(default=dict)
