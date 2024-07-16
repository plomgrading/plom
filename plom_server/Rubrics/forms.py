# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Divy Patel
# Copyright (C) 2024 Colin B. Macdonald
# Copyright (C) 2024 Aden Chan

from django import forms

from Papers.services import SpecificationService

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
    KIND_CHOICES = [
        ("", "All Kinds"),
        ("absolute", "Absolute"),
        ("neutral", "Neutral"),
        ("relative", "Relative"),
    ]

    question_filter = forms.TypedChoiceField(required=False)
    kind_filter = forms.TypedChoiceField(choices=KIND_CHOICES, required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        question_choices = [
            (str(q_idx), q_label)
            for q_idx, q_label in SpecificationService.get_question_index_label_pairs()
        ]
        self.fields["question_filter"].choices = question_choices


class RubricEditForm(forms.ModelForm):
    class Meta:
        model = Rubric
        fields = ["meta"]
        widgets = {
            "meta": forms.Textarea(attrs={"rows": 2, "cols": 50}),
        }


class RubricDownloadForm(forms.Form):
    FILE_TYPE_CHOICES = [("csv", ".csv"), ("json", ".json"), ("toml", ".toml")]
    question_filter = forms.TypedChoiceField(required=False)
    file_type = forms.TypedChoiceField(
        choices=FILE_TYPE_CHOICES, required=False, initial=".csv"
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        question_choices = [
            (str(q_idx), q_label)
            for q_idx, q_label in SpecificationService.get_question_index_label_pairs()
        ]

        question_choices.insert(0, ("", "All Questions"))

        self.fields["question_filter"].choices = question_choices


class RubricUploadForm(forms.Form):
    rubric_file = forms.FileField(label="")


class RubricDiffForm(forms.Form):
    left_compare = forms.ModelChoiceField(queryset=None)
    right_compare = forms.ModelChoiceField(queryset=None)

    def __init__(self, *args, **kwargs):
        key = kwargs.pop("key", None)
        super().__init__(*args, **kwargs)

        if key:
            queryset = Rubric.objects.filter(key=key)
            self.fields["left_compare"].queryset = queryset
            self.fields["left_compare"].label_from_instance = (
                lambda obj: "Rev. %i" % obj.revision
            )

            self.fields["right_compare"].queryset = queryset
            self.fields["right_compare"].label_from_instance = (
                lambda obj: "Rev. %i" % obj.revision
            )
