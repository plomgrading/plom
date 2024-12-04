# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Julian Lapenna
# Copyright (C) 2023 Edith Coates
# Copyright (C) 2024 Aidan Murphy

import csv
from io import StringIO

from django import forms
from django.conf import settings
from django.core.validators import FileExtensionValidator
from django.core.exceptions import ValidationError


def validate_file_size(value):
    filesize = value.size

    if filesize > settings.MAX_FILE_SIZE:
        raise ValidationError(
            "The maximum file size that can be uploaded is {settings.MAX_FILE_SIZE / 1e6}MB"
        )
    else:
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
            data = csv.reader(StringIO(file), delimiter=",")
            # check that the header is correct
            header = next(data)
            if header != ["Paper Number", "Question Number", "Priority Value"]:
                raise ValidationError(
                    "Invalid csv header. Please use the following headers: "
                    + "'Paper Number', 'Question Number', 'Priority Value'."
                )
        except csv.Error:
            raise ValidationError("Invalid csv file")
        return data
