# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates

import pathlib
import hashlib
import fitz
from fitz import FileDataError
from datetime import datetime

from django import forms
from django.forms import ValidationError
from django.utils.text import slugify


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

        # TODO: compare against pdf.size if we want to specify a max file size in future

        # correct format, readable by fitz, not a duplicate?
        try:
            file_bytes = pdf.read()
            pdf_doc = fitz.open(stream=file_bytes)
            if "PDF" not in pdf_doc.metadata["format"]:
                raise ValidationError("File is not a valid PDF.")

            # TODO: Should we prevent uploading duplicate bundles or warn them?
            hashed = hashlib.sha256(file_bytes).hexdigest()

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
