# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2023 Colin B. Macdonald

from django import forms


class UploadErrorImageForm(forms.Form):
    pass


class AnnotationFilterForm(forms.Form):
    DAY_CHOICES = [
        ("0", "0"),
        ("1", "1"),
        ("2", "2"),
        ("3", "3")
    ]

    HOUR_CHOICES = [
        ("0", "0"),
        ("1", "1"),
    ]

    # MINUTE_CHOICES = [
    #     ("", 0),
    #     ("1", "1"),
    # ]

    # SECONDS_CHOICES = [
    #     ("", 0),
    #     ("1", "1"),
    # ]

    day_filter = forms.TypedChoiceField(choices=DAY_CHOICES, required=False)
    hour_filter = forms.TypedChoiceField(choices=HOUR_CHOICES, required=False)
    # minute_filter = forms.TypedChoiceField(choices=MINUTE_CHOICES, required=False)
    # second_filter = forms.TypedChoiceField(choices=SECONDS_CHOICES, required=False)
