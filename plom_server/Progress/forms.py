# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2023 Colin B. Macdonald

from django import forms


class UploadErrorImageForm(forms.Form):
    pass


class AnnotationFilterForm(forms.Form):
    DAY_CHOICES = [
        ("0", ""),
        ("1", "a day ago"),
        ("2", "2 days ago"),
        ("3", "3 days ago"),
    ]

    HOUR_CHOICES = [
        ("0", ""),
        ("1", "an hour ago"),
        ("2", "2 hours ago"),
        ("3", "3 hours ago"),
    ]

    MINUTE_CHOICES = [
        ("0", ""),
        ("1", "a minute ago"),
        ("2", "2 minutes ago"),
        ("5", "5 minutes ago"),
        ("10", "10 minutes ago"),
        ("15", "15 minutes ago"),
        ("30", "30 minutes ago"),
        ("40", "40 minutes ago"),
        ("50", "50 minutes ago"),
    ]

    # SECONDS_CHOICES = [
    #     ("", 0),
    #     ("1", "1"),
    # ]

    day_filter = forms.TypedChoiceField(
        choices=DAY_CHOICES, required=False, label="Days "
    )
    hour_filter = forms.TypedChoiceField(
        choices=HOUR_CHOICES, required=False, label="Hours "
    )
    minute_filter = forms.TypedChoiceField(
        choices=MINUTE_CHOICES, required=False, label="Minutes "
    )
    # second_filter = forms.TypedChoiceField(choices=SECONDS_CHOICES, required=False)
