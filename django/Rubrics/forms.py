# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Julian Lapenna

from django import forms

class RubricForm(forms.Form):
   option1 = forms.BooleanField(required=False, label='option1')
   option2 = forms.BooleanField(required=False, label='option2')
   option3 = forms.BooleanField(required=False, label='option3')
