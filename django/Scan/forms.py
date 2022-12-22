# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2022 Brennen Chiu

import pathlib
import hashlib
import fitz
from fitz import FileDataError
from datetime import datetime

from django import forms
from django.forms import ValidationError
from django.utils.text import slugify
from django.conf import settings

from Scan.services import ScanService


class BundleUploadForm(forms.Form):
    """
    Upload a bundle PDF
    """

    pdf = forms.FileField(
        allow_empty_file=False,
        max_length=100,
        label="",
        widget=forms.FileInput(attrs={"accept": "application/pdf"}),
    )

    def clean(self):
        data = self.cleaned_data
        pdf = data["pdf"]

        # TODO: set a request size limit in production
        if pdf.size > settings.MAX_BUNDLE_SIZE:
            readable_file_size = settings.MAX_BUNDLE_SIZE / 1e9
            raise ValidationError(f"Bundle size limit is {readable_file_size} GB.")

        # correct format, readable by fitz, not a duplicate?
        try:
            file_bytes = pdf.read()
            pdf_doc = fitz.open(stream=file_bytes)
            if "PDF" not in pdf_doc.metadata["format"]:
                raise ValidationError("File is not a valid PDF.")

            # TODO: Should we prevent uploading duplicate bundles or warn them?
            hashed = hashlib.sha256(file_bytes).hexdigest()
            scanner = ScanService()
            if scanner.check_for_duplicate_hash(hashed):
                raise ValidationError("Bundle was already uploaded.")

            # get slug
            filename_stem = pathlib.Path(str(pdf)).stem
            slug = slugify(filename_stem)

            data.update(
                {
                    "pdf_doc": pdf_doc,
                    "slug": slug,
                    "time_uploaded": datetime.now(),
                    "sha256": hashed,
                }
            )
            return data
        except (FileDataError, KeyError):
            raise ValidationError("Unable to open file.")


class FlagImageForm(forms.Form):
    """
    A form to flag the images with error to the manager
    Added comment to show what the error is.
    """

    comment = forms.CharField(
        label="Comment",
        widget=forms.Textarea(
            attrs={
                "class": "comment-input",
                "placeholder": "Comment to manager about this page (optional)",
                "name": "comment",
                "style": "display: block; width: 100%; height: 100px; border-radius: 0.375rem; margin-bottom: 4px;",
            }
        ),
        required=False,
    )


class ReplaceImageForm(forms.Form):
    """
    Replace an error page image form.
    """
    single_pdf = forms.FileField(
        allow_empty_file=False,
        max_length=100,
        label="",
        widget=forms.FileInput(attrs={"accept": "application/pdf"}),
    )

    # def clean(self):
    #     data = self.cleaned_data
    #     single_pdf = data["single_pdf"]

    #     # set a file size?
    #     # if single_pdf.size > settings.MAX_FILE_SIZE:
    #     #     readable_single_file_size = settings.MAXFILE_SIZE / 1e6
    #     #     raise ValidationError(f"File size limit is {readable_single_file_size} MB.")
        
        
    #     try:
    #         # make sure it is correct format
    #         file_bytes = single_pdf.read()
    #         pdf_doc = fitz.open(stream=file_bytes)
    #         if "PDF" not in pdf_doc.metadata["format"]:
    #             raise ValidationError("File is not a valid PDF.")
    #         # make sure only 1 pdf page
    #     except (FileDataError, KeyError):
    #         raise ValidationError("Unable to open file.")
    #     # turn that pdf file into page image 
    #     # check for duplicate page image
