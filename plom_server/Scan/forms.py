# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2022-2023 Brennen Chiu
# Copyright (C) 2023-2025 Andrew Rechnitzer
# Copyright (C) 2023-2025 Colin B. Macdonald
# Copyright (C) 2024 Aidan Murphy

import pathlib

from django import forms
from django.forms import ValidationError
from django.utils.text import slugify


class BundleUploadForm(forms.Form):
    """Django form for upload of a bundle PDF."""

    pdf = forms.FileField(
        allow_empty_file=False,
        label="",
        widget=forms.FileInput(attrs={"accept": "application/pdf"}),
    )
    # TODO: above doesn't prevent non-PDF with current form, consider removing
    force_render = forms.BooleanField(required=False)
    read_after = forms.BooleanField(required=False)
    accept_duplicates = forms.BooleanField(required=False)

    def clean(self):
        data = self.cleaned_data
        pdf = data.get("pdf")
        if not pdf:
            raise ValidationError("Data must include a PDF file via the 'pdf' field")

        # NOTE - this is where we enforce bundle names avoiding underscores
        # reserving those for system bundles.
        if pdf.name.startswith("_"):
            raise ValidationError(
                "Bundle filenames cannot start with an underscore - we reserve those for internal use."
            )

        # get slug from filename
        filename_stem = pathlib.Path(pdf.name).stem
        slug = slugify(filename_stem)

        data.update(
            {
                "slug": slug,
            }
        )
        return data
