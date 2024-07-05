# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Elisa Pan

from django import forms
from .models import PedagogyTag


class AddTagForm(forms.Form):
    question_index = forms.IntegerField()
    tag_id = forms.ModelChoiceField(queryset=PedagogyTag.objects.all())


class RemoveTagForm(forms.Form):
    question_tag_id = forms.IntegerField()
