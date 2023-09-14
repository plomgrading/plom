# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2023 Colin B. Macdonald
# Copyright (C) 2023 Brennen Chiu

from django import forms


class AnnotationFilterForm(forms.Form):
    TIME_CHOICES = [
        ("", ""),
        ("300", "the last 5 minutes"),
        ("1800", "the last 30 minutes"),
        ("3600", "the last hour"),
        ("7200", "the last 2 hours"),
        ("10800", "the last 3 hours"),
        ("21600", "the last 6 hours"),
        ("86400", "the last day"),
    ]

    time_filter_seconds = forms.TypedChoiceField(
        choices=TIME_CHOICES,
        coerce=int,
        required=False,
        label="Filter for annotations created in",
    )
