from operator import mod
import os
import shutil
import re
import pathlib
from django.db import models
from django.db.models.signals import pre_delete
from django.dispatch import receiver
from django.utils.text import slugify
from jinja2 import ModuleLoader

"""
TODO: move util functions outside models file, clean up old functions
"""

def unique_slug(filename):
    """
    Generate a slug from the input filename, and append '-copy' if that file already exists on disk
    """
    slug = slugify(re.sub('.pdf$', '', filename))
    while os.path.exists(pathlib.Path('TestCreator') / 'media' / f'{slug}.pdf'):
        slug = slug + '-copy'
    return slug

# just a simple folder for media for now
def temp_filename_path(instance, filename):
    slug = slugify(re.sub('.pdf$', '', filename))
    return pathlib.Path('TestCreator') / 'media' / f'{slug}.pdf'

class ReferencePDF(models.Model):
    # TODO: use TextField instead of CharField, don't hardcode field lengths!
    filename_slug = models.CharField(max_length=100, default='')
    pdf = models.FileField(upload_to=temp_filename_path)
    num_pages = models.IntegerField(default=0)

def pre_delete_reference_pdf(sender, instance, **kwargs):
    # delete thumbnails
    thumbnail_folder = pathlib.Path('TestCreator') / 'static' / 'thumbnails' / instance.filename_slug
    if thumbnail_folder.exists():
        shutil.rmtree(thumbnail_folder)

    # delete pdf from disk
    pdf_path = pathlib.Path('TestCreator') / 'media' / f'{instance.filename_slug}.pdf'
    if pdf_path.exists():
        os.remove(pdf_path)

pre_delete.connect(
    pre_delete_reference_pdf, sender=ReferencePDF
)


class TestSpecInfo(models.Model):
    long_name = models.TextField()
    short_name = models.TextField()
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
