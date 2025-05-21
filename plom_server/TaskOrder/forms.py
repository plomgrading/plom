# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Julian Lapenna
# Copyright (C) 2023 Edith Coates
# Copyright (C) 2024 Aidan Murphy
# Copyright (C) 2025 Colin B. Macdonald
# Copyright (C) 2025 Bryan Tanady

import csv
from io import StringIO

from django import forms
from django.conf import settings
from django.core.validators import FileExtensionValidator
from django.forms import ValidationError


def validate_file_size(value):
    """A helper function, it raises an error if input file is too big."""
    filesize = value.size

    if filesize > settings.MAX_FILE_SIZE:
        raise ValidationError(
            f"The maximum file size that can be uploaded is {settings.MAX_FILE_SIZE_DISPLAY}"
        )
    return value


class TaskOrderForm(forms.Form):
    """Form for selecting the order to set task priorities."""

    order_tasks_by = forms.ChoiceField(
        choices=(
            ("papernum", "by Paper number (default)"),
            ("shuffle", "Shuffle task order"),
            ("custom", "Custom order (requires CSV upload)"),
        ),
        widget=forms.RadioSelect,
        required=True,
    )


class UploadFileForm(forms.Form):
    """Form for uploading a CSV file of task priorities."""

    file = forms.FileField(
        validators=[FileExtensionValidator(["csv"]), validate_file_size],
        required=False,
    )

    def clean_file(self):
        try:
            file = self.cleaned_data["file"].read().decode("utf-8")
            # Attempt to parse the file as csv
            data = csv.DictReader(StringIO(file))
            header = data.fieldnames
            expected_header = ["Paper Number", "Question Index", "Priority Value"]
            # check that the header contains all required cols
            if not header or not set(expected_header).issubset(set(header)):
                raise ValidationError(
                    "Invalid csv header. Please use the following headers: "
                    f"Expecting {expected_header} but got {header}"
                )
        except csv.Error as e:
            raise ValidationError(f"Invalid csv file: {e}")
        return data
