# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2023 Colin B. Macdonald

from django import forms
from django.utils import timezone

class AnnotationFilterForm(forms.Form):
    TIME_CHOICES = [
        ("", ""),
        ("60", "a minute ago"),
        ("120", "2 minutes ago"),
        ("300", "5 minutes ago"),
        ("600", "10 minutes ago"),
        ("1200", "20 minutes ago"),
        ("1800", "30 minutes ago"),
        ("2400", "40 minutes ago"),
        ("3000", "50 minutes ago"),
        ("3600", "an hour ago"),
        ("5400", "an hour and a half ago"),
        ("7200", "2 hours ago"),
        ("10800", "3 hours ago"),
        ("86400", "a day ago")
    ]

    time_filter = forms.TypedChoiceField(
        choices=TIME_CHOICES, required=False, label="Select a time to filter"
    )
