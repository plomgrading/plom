# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Bryan Tanady

from django import forms


class StudentIDForm(forms.Form):
    INPUT_CHOICES = [("paper_number", "Paper Number"), ("StudentID", "Student ID")]

    choice = forms.ChoiceField(
        required=True,
        widget=forms.RadioSelect,
        choices=INPUT_CHOICES,
        label="Input type:",
    )

    input = forms.CharField(
        required=True,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Enter Input"}
        ),
        label="",
    )
