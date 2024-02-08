# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Divy Patel
# Copyright (C) 2024 Colin B. Macdonald

from django import forms

from .models import Rubric


class RubricAdminForm(forms.Form):
    pass
    # TODO: "Also create the +1, +2, -1, -2, "naked delta" rubrics"
    # TODO: Issue #2915
    # create_naked_deltas = forms.BooleanField(
    #     required=False, widget=forms.CheckboxInput(attrs={"checked": True})
    # )


class RubricWipeForm(forms.Form):
    I_am_sure = forms.BooleanField()
    confirm_by_typing_the_short_name = forms.CharField()


class RubricFilterForm(forms.Form):
    # using hard-coded choices for now
    QUESTION_CHOICES = [
        ("", "All Questions"),
        ("1", "Question 1"),
        ("2", "Question 2"),
        ("3", "Question 3"),
    ]
    KIND_CHOICES = [
        ("", "All Kinds"),
        ("absolute", "Absolute"),
        ("neutral", "Neutral"),
        ("relative", "Relative"),
    ]

    question_filter = forms.TypedChoiceField(choices=QUESTION_CHOICES, required=False)
    kind_filter = forms.TypedChoiceField(choices=KIND_CHOICES, required=False)


class RubricEditForm(forms.ModelForm):
    class Meta:
        model = Rubric
        fields = ["meta"]
        widgets = {
            "meta": forms.Textarea(attrs={"rows": 2, "cols": 50}),
        }
