# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Aden Chan

from django import forms

class CompleteWipeForm(forms.Form):
    confirmation_field = forms.CharField()