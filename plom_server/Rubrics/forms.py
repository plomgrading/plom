# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Divy Patel
# Copyright (C) 2024-2026 Colin B. Macdonald
# Copyright (C) 2024 Aden Chan
# Copyright (C) 2024 Andrew Rechnitzer
# Copyright (C) 2025 Deep Shah

from django import forms

from plom_server.Papers.services import SpecificationService

from .models import Rubric


class RubricCreateHalfMarkForm(forms.Form):
    # creates half-mark rubrics
    pass


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
            revs = Rubric.objects.filter(rid=rid).order_by("revision")
            self.fields["left_compare"].queryset = revs
            self.fields["left_compare"].label_from_instance = (
                lambda obj: f"Rev. {obj.revision}.{obj.subrevision}"
            )

            self.fields["right_compare"].queryset = revs
            self.fields["right_compare"].label_from_instance = (
                lambda obj: f"Rev. {obj.revision}.{obj.subrevision}"
            )


class RubricItemForm(forms.ModelForm):
    """Form for creating or updating a Rubric."""

    question_index = forms.TypedChoiceField(
        required=True,
        widget=forms.Select(attrs={"onchange": "updateQuestion()"}),
        empty_value="",
    )

    # Note: DecimalField seems to result in ugly "+3.0" rubrics
    # Note: "value" is not required for Neutral rubrics
    value = forms.FloatField(required=False)

    kind = forms.ChoiceField(
        choices=Rubric.RubricKind.choices,
        initial=Rubric.RubricKind.ABSOLUTE,
        widget=forms.Select(attrs={"onchange": "updateKind()"}),
    )
    out_of = forms.IntegerField(
        required=False,
        widget=forms.NumberInput(attrs={"onchange": "updateValueConstraints()"}),
    )
    published = forms.BooleanField(required=False, label="Published", initial=True)

    class Meta:
        model = Rubric
        fields = [
            "question_index",
            "text",
            "kind",
            "value",
            "out_of",
            "meta",
            "versions",
            "parameters",
            "tags",
            "pedagogy_tags",
            "published",
        ]
        widgets = {
            "text": forms.Textarea(attrs={"rows": 3}),
            "meta": forms.Textarea(attrs={"rows": 2}),
            "tags": forms.TextInput(),  # default would be Textarea
            "parameters": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        question_choices = [
            (str(q_idx), q_label)
            for q_idx, q_label in SpecificationService.get_question_index_label_pairs()
        ]

        self.fields["question_index"].choices = question_choices

        for field in self.fields:
            self.fields[field].widget.attrs["class"] = "form-control"


class RubricTemplateDownloadForm(forms.Form):
    """Form for downloading a template of rubrics."""

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
