# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Bryan Tanady

from django import forms
from .models import ClusteringModelType


class ClusteringJobForm(forms.Form):
    """Form used to create a background clustering job"""

    choice = forms.ChoiceField(
        choices=ClusteringModelType.choices,
        widget=forms.RadioSelect(
            attrs={
                "class": "form-radio text-blue-600 focus:ring-blue-500",
            }
        ),
        label="Pick answer type for clustering",
    )
    question = forms.IntegerField(widget=forms.HiddenInput())
    version = forms.IntegerField(widget=forms.HiddenInput())
    page_num = forms.IntegerField(widget=forms.HiddenInput())
    top = forms.FloatField(widget=forms.HiddenInput())
    left = forms.FloatField(widget=forms.HiddenInput())
    bottom = forms.FloatField(widget=forms.HiddenInput())
    right = forms.FloatField(widget=forms.HiddenInput())
