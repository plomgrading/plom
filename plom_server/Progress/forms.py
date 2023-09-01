# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2023 Colin B. Macdonald

from django import forms
from django.utils import timezone


class AnnotationFilterForm(forms.Form):
    TIME_CHOICES = [
        ("", ""),
        ("300", "5 minutes ago"),
        ("1800", "30 minutes ago"),
        ("3600", "an hour ago"),
        ("7200", "2 hours ago"),
        ("10800", "3 hours ago"),
        ("21600", "6 hours ago"),
        ("86400", "a day ago"),
    ]

    time_filter = forms.TypedChoiceField(
        choices=TIME_CHOICES, coerce=int, required=False, label="Select a time to filter"
    )
