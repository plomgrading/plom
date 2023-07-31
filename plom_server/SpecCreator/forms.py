# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2023 Colin B. Macdonald

import re

import fitz

from django import forms
from django.core.exceptions import ValidationError

from .services import StagingSpecificationService
from . import models


class TestSpecNamesForm(forms.Form):
    long_name = forms.CharField(
        max_length=100,
        label="Long name:",
        help_text='The full name of the test, for example "Maths101 Midterm 2"',
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )

    short_name = forms.CharField(
        max_length=50,
        label="Name:",
        help_text='The short name of the test, for example "m101mt2"',
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )

    versions = forms.IntegerField(
        label="Number of versions:",
        help_text="For shuffling questions over multiple test papers.",
        widget=forms.NumberInput(attrs={"class": "form-control", "min": 1}),
    )


class TestSpecVersionsRefPDFForm(forms.Form):
    pdf = forms.FileField(
        allow_empty_file=False,
        max_length=100,
        label="Reference PDF:",
        help_text="Upload a PDF of a test version for rendering page thumbnails.",
        widget=forms.FileInput(
            attrs={"accept": "application/pdf", "class": "form-control"}
        ),
    )

    def clean(self):
        data = self.cleaned_data
        pdf = data["pdf"]

        # validate that file is a PDF
        pdf_doc = fitz.open(stream=pdf.read())
        if "PDF" not in pdf_doc.metadata["format"]:
            raise ValidationError("File is not a valid PDF.")

        data["num_pages"] = pdf_doc.page_count

        return data


class TestSpecPDFSelectForm(forms.Form):
    def __init__(self, n_pages, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for i in range(n_pages):
            self.fields.update(
                {
                    f"page{i}": forms.BooleanField(
                        required=False,
                        widget=forms.HiddenInput(
                            attrs={"x-bind:value": f"page{i}selected"}
                        ),
                    )
                }
            )


class TestSpecIDPageForm(TestSpecPDFSelectForm):
    def clean(self):
        data = self.cleaned_data
        selected_pages = [key for key in data.keys() if data[key]]
        if len(selected_pages) > 1:
            raise ValidationError("Test can have only one ID page.")

        return data


class TestSpecQuestionsMarksForm(forms.Form):
    questions = forms.IntegerField(
        label="Number of questions:",
        widget=forms.NumberInput(
            attrs={"class": "form-control", "id": "curr_questions", "min": 1, "max": 50}
        ),
    )
    total_marks = forms.IntegerField(
        label="Total marks:",
        widget=forms.NumberInput(attrs={"class": "form-control", "min": 1}),
    )

    def clean(self):
        data = self.cleaned_data

        if data["total_marks"] < data["questions"]:
            raise ValidationError(
                "Number of questions should not exceed the total marks."
            )

        if data["questions"] > 50:
            # TODO: be nicer
            raise ValidationError("Your test is too long!")


class SpecQuestionDetailsForm(TestSpecPDFSelectForm):
    label = forms.CharField(
        max_length=15,
        label="Label:",
        help_text="Question label. Default Q(i)",
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    mark = forms.IntegerField(
        label="Mark:",
        widget=forms.NumberInput(attrs={"class": "form-control", "min": 0}),
    )
    shuffle = forms.ChoiceField(
        label="Shuffle:",
        choices=models.SHUFFLE_CHOICES,
        help_text="Shuffle over test versions, or use first version",
        widget=forms.RadioSelect(attrs={"class": "form-check-input"}),
    )

    def __init__(self, *args, **kwargs):
        if "q_idx" in kwargs.keys():
            self.question_idx = kwargs.pop("q_idx")
        super().__init__(*args, **kwargs)

    def clean(self):
        data = self.cleaned_data

        # Are the marks less than the test's total marks?
        spec = StagingSpecificationService()
        if data["mark"] > spec.get_total_marks():
            raise ValidationError("Question cannot have more marks than the test.")

        selected_pages = []
        for key, value in data.items():
            if "page" in key and value:
                selected_pages.append(int(re.sub(r"\D", "", key)))
        selected_pages = sorted(selected_pages)

        # Was at least one page selected?
        if len(selected_pages) < 1:
            raise ValidationError("At least one page must be selected.")

        # Are the selected pages next to each other?
        for i in range(len(selected_pages) - 1):
            curr = selected_pages[i]
            next = selected_pages[i + 1]

            if next - curr > 1:
                raise ValidationError("Question pages must be consecutive.")

        # Is this question assigned to pages after earlier questions?
        if self.question_idx:
            page_list = spec.get_page_list()
            for i in range(
                selected_pages[-1] + 1, len(page_list)
            ):  # all pages after this one
                page_i = page_list[i]
                other_question = page_i["question_page"]
                if other_question and other_question < self.question_idx:
                    raise ValidationError(
                        f"Question {self.question_idx} cannot come before question {other_question}."
                    )


class SpecValidateForm(forms.Form):
    def clean(self):
        """Clean up and check.

        Things to check:

        Is there a long name and a short name?

        Are there test versions, num_to_produce, and a reference PDF?

        Is there an ID page?

        Are there questions?

        Do all the questions have pages attached?

        Do all the questions have the relevant fields?

        Are all the pages selected by something?
        """
        spec = StagingSpecificationService()
        try:
            spec.validate_specification()
        except ValueError as e:
            raise ValidationError(e)
