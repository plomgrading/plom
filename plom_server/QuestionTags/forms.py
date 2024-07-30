# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Elisa Pan
# Copyright (C) 2024 Colin B. Macdonald

from django import forms
from .models import PedagogyTag


class AddTagForm(forms.Form):
    """Form for adding a tag to a question.

    Fields:
        question_index: The index of the question to be tagged.
        tag_id: The ID of the tag to be added, selected from existing PedagogyTag objects.
        confidential_info: text that is shown to instructors, hidden to students.
    """

    question_index = forms.IntegerField()
    tag_id = forms.ModelChoiceField(queryset=PedagogyTag.objects.all())
    # TODO: Colin confused by CharField here and TextField in the model.
    # TODO: Elisa: CharField(widget=forms.Textarea) might be better (?)
    confidential_info = forms.CharField(required=False)


class RemoveTagForm(forms.Form):
    """Form for removing a tag from a question.

    Fields:
        question_tag_id: The ID of the question-tag link to be removed.
    """

    question_tag_id = forms.IntegerField()
