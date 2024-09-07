# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2022-2023 Brennen Chiu
# Copyright (C) 2023-2024 Andrew Rechnitzer
# Copyright (C) 2023-2024 Colin B. Macdonald
# Copyright (C) 2024 Aidan Murphy

import hashlib
import pathlib

import pymupdf as fitz

from django.utils import timezone
from django import forms
from django.forms import ValidationError
from django.utils.text import slugify
from django.conf import settings

from .services import ScanService


class BundleUploadForm(forms.Form):
    """Django form for upload of a bundle PDF."""

    pdf = forms.FileField(
        allow_empty_file=False,
        label="",
        widget=forms.FileInput(attrs={"accept": "application/pdf"}),
    )
    force_render = forms.BooleanField(required=False)
    read_after = forms.BooleanField(required=False)

    def clean(self):
        data = self.cleaned_data
        pdf = data["pdf"]

        # TODO: set a request size limit in production
        if pdf.size > settings.MAX_BUNDLE_SIZE:
            readable_file_size = settings.MAX_BUNDLE_SIZE / 1e9
            raise ValidationError(f"Bundle size limit is {readable_file_size} GB.")

        if pdf.name.startswith("_"):
            raise ValidationError(
                "Bundle filenames cannot start with an underscore - we reserve those for internal use."
            )

        # correct format, readable by fitz, not a duplicate?
        try:
            file_bytes = pdf.read()

            # TODO: Should we prevent uploading duplicate bundles or warn them?
            hashed = hashlib.sha256(file_bytes).hexdigest()
            scanner = ScanService()
            if scanner.check_for_duplicate_hash(hashed):
                original_bundle_name = scanner.get_bundle_name_from_hash(hashed)
                raise ValidationError(
                    f"Bundle was already uploaded as '{original_bundle_name}' and hash {hashed}"
                )

            # get slug
            filename_stem = pathlib.Path(str(pdf)).stem
            slug = slugify(filename_stem)

            with fitz.open(stream=file_bytes) as pdf_doc:
                if "PDF" not in pdf_doc.metadata["format"]:
                    raise ValidationError("File is not a valid PDF.")
                if pdf_doc.page_count > settings.MAX_BUNDLE_PAGES:
                    raise ValidationError(
                        f"File exceeds {settings.MAX_BUNDLE_PAGES} page limit."
                    )
                data.update(
                    {
                        "number_of_pages": pdf_doc.page_count,
                        "slug": slug,
                        "time_uploaded": timezone.now(),
                        "sha256": hashed,
                    }
                )
            return data
        except (fitz.FileDataError, KeyError) as e:
            raise ValidationError(f"Unable to open file: {e}")
