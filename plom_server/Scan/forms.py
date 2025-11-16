# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2022-2023 Brennen Chiu
# Copyright (C) 2023-2025 Andrew Rechnitzer
# Copyright (C) 2023-2025 Colin B. Macdonald
# Copyright (C) 2024 Aidan Murphy

import hashlib
import pathlib

import pymupdf

from django.utils import timezone
from django import forms
from django.forms import ValidationError
from django.utils.text import slugify
from django.conf import settings


class BundleUploadForm(forms.Form):
    """Django form for upload of a bundle PDF.

    TODO: There is some duplicated code/effort with ScanListBundles API
    endpoint which uses the DRF rather than Forms.  If one makes changes
    here, look there as well.
    """

    pdf = forms.FileField(
        allow_empty_file=False,
        label="",
        widget=forms.FileInput(attrs={"accept": "application/pdf"}),
    )
    force_render = forms.BooleanField(required=False)
    read_after = forms.BooleanField(required=False)
    accept_duplicates = forms.BooleanField(required=False)

    def clean(self):
        data = self.cleaned_data
        pdf = data.get("pdf")
        if not pdf:
            raise ValidationError("Data must include a PDF file via the 'pdf' field")

        # TODO: set a request size limit in production
        if pdf.size > settings.MAX_BUNDLE_SIZE:
            readable_file_size = settings.MAX_BUNDLE_SIZE / 1e9
            raise ValidationError(f"Bundle size limit is {readable_file_size} GB.")

        # NOTE - this is where we enforce bundle names avoiding underscores
        # reserving those for system bundles.
        if pdf.name.startswith("_"):
            raise ValidationError(
                "Bundle filenames cannot start with an underscore - we reserve those for internal use."
            )

        file_bytes = pdf.read()

        hashed = hashlib.sha256(file_bytes).hexdigest()
        # get slug from filename
        filename_stem = pathlib.Path(pdf.name).stem
        slug = slugify(filename_stem)

        try:
            with pymupdf.open(stream=file_bytes) as pdf_doc:
                if "PDF" not in pdf_doc.metadata["format"]:
                    raise ValidationError("File is not a valid PDF.")
                if pdf_doc.page_count > settings.MAX_BUNDLE_PAGES:
                    raise ValidationError(
                        f"File of {pdf_doc.page_count} pages "
                        f"exceeds {settings.MAX_BUNDLE_PAGES} page limit."
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
        except (pymupdf.FileDataError, KeyError) as e:
            raise ValidationError(f"Unable to open file: {e}") from e
        except pymupdf.mupdf.FzErrorBase as e:
            # https://github.com/pymupdf/PyMuPDF/issues/3905
            # Drop this case once our minimum PyMuPDF >= 1.24.11
            raise ValidationError(
                f"Perhaps not a pdf file?  Unexpected error: {e}"
            ) from e
