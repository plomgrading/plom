# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Julian Lapenna

from django import forms

class TagFormFilter(forms.Form):
    tag_filter_text = forms.CharField(required=False, widget=forms.TextInput, label="Tag Text")
    strict_match = forms.BooleanField(required=False, label="Strict Match")
   