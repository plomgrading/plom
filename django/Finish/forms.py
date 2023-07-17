# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Julian Lapenna

from django import forms


class StudentMarksFilterForm(forms.Form):
    version_info = forms.BooleanField(required=False, label="Version Information")
    timing_info = forms.BooleanField(required=False, label="Timing Information")
    warning_info = forms.BooleanField(required=False, label="Warning Information")
