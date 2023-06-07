# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Julian Lapenna

from django import forms

class TagFormFilter(forms.Form):
    text_entry1 = forms.CharField(required=False, widget=forms.TextInput, label='tag_filter')
    strict_match = forms.BooleanField(required=False, label='strict_match')
   