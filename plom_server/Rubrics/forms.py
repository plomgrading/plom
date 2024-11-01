# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Divy Patel
# Copyright (C) 2024 Colin B. Macdonald
# Copyright (C) 2024 Aden Chan
# Copyright (C) 2024 Andrew Rechnitzer

from django import forms

from Papers.services import SpecificationService

from .models import Rubric


class RubricHalfMarkForm(forms.Form):
    # creates half-mark rubrics
    pass


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

    SYSTEM_CHOICES = [
        ("", "All Types"),
        ("System", "System"),
        ("User", "User"),
    ]

    question_filter = forms.TypedChoiceField(required=False)
    kind_filter = forms.TypedChoiceField(choices=KIND_CHOICES, required=False)
    system_filter = forms.TypedChoiceField(choices=SYSTEM_CHOICES, required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        question_choices = [
            (str(q_idx), q_label)
            for q_idx, q_label in SpecificationService.get_question_index_label_pairs()
        ]
        question_choices.insert(0, ("", "All Questions"))
        self.fields["question_filter"].choices = question_choices


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
    """Form for comparing two rubrics."""

    left_compare = forms.ModelChoiceField(queryset=None)
    right_compare = forms.ModelChoiceField(queryset=None)

    def __init__(self, *args, **kwargs):
        rid = kwargs.pop("rid", None)
        super().__init__(*args, **kwargs)

        if rid:
            queryset = Rubric.objects.filter(rid=rid)
            self.fields["left_compare"].queryset = queryset
            self.fields["left_compare"].label_from_instance = (
                lambda obj: "Rev. %i" % obj.revision
            )

            self.fields["right_compare"].queryset = queryset
            self.fields["right_compare"].label_from_instance = (
                lambda obj: "Rev. %i" % obj.revision
            )


class RubricItemForm(forms.ModelForm):
    """Form for creating or updating a Rubric."""

    question = forms.TypedChoiceField(
        required=True,
        widget=forms.Select(attrs={"onchange": "updateQuestion()"}),
        empty_value="",
    )

    # Explicit IntegerField for value for now
    # TODO: Change this to a DecimalField when ready
    value = forms.IntegerField(required=True)

    kind = forms.ChoiceField(
        choices=Rubric.RubricKind.choices,
        initial=Rubric.RubricKind.ABSOLUTE,
        widget=forms.Select(attrs={"onchange": "updateKind()"}),
    )
    out_of = forms.IntegerField(required=False)
    versions = forms.MultipleChoiceField(required=False)

    class Meta:
        model = Rubric
        fields = [
            "text",
            "kind",
            "value",
            "out_of",
            "meta",
            "versions",
            "parameters",
            "pedagogy_tags",
        ]
        widgets = {
            "text": forms.Textarea(attrs={"rows": 3}),
            "meta": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        question_choices = [
            (str(q_idx), q_label)
            for q_idx, q_label in SpecificationService.get_question_index_label_pairs()
        ]

        self.fields["question"].choices = question_choices
        self.fields["out_of"].widget.attrs["readonly"] = True

        version_choices = [
            (str(v_idx), v_idx)
            for v_idx in range(1, SpecificationService.get_n_versions() + 1)
        ]
        self.fields["versions"].choices = version_choices

        for field in self.fields:
            self.fields[field].widget.attrs["class"] = "form-control"
