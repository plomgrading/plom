# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Brennen Chiu
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2023 Colin B. Macdonald

from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django import forms

"""
This is the collection of forms to be use in a website.
Also can customize the default form that django gives us.
"""


class CreateUserForm(UserCreationForm):
    username = forms.CharField(max_length=40, help_text="Username")
    email = forms.EmailField(max_length=100, help_text="Email", required=False)

    def __init__(self, *args, **kwargs):
        super(CreateUserForm, self).__init__(*args, **kwargs)
        self.fields["password1"].required = False
        self.fields["password2"].required = False
        self.fields["password1"].widget.attrs["autocomplete"] = "off"
        self.fields["password2"].widget.attrs["autocomplete"] = "off"

    class Meta:
        model = User
        fields = ["username", "email"]


class CreateScannersAndMarkersForm(forms.Form):
    USERNAME_CHOICES = [
        ("basic", "Basic numbered usernames"),
        (
            "funky",
            "\N{LEFT DOUBLE QUOTATION MARK}Funky\N{RIGHT DOUBLE QUOTATION MARK} usernames (such as \N{LEFT DOUBLE QUOTATION MARK}hungryHeron8\N{RIGHT DOUBLE QUOTATION MARK})",
        ),
    ]

    num_users = forms.IntegerField(
        widget=forms.NumberInput(
            attrs={
                "class": "form-control mb-1",
                "style": "max-width: 23rem; min-width: 4.5rem",
                "min": 1,
                "max": 100,
                "name": "num_users",
            }
        ),
        initial=1,
    )

    basic_or_funky_username = forms.CharField(
        label="What sort of usernames would you like?",
        widget=forms.RadioSelect(choices=USERNAME_CHOICES, attrs={"class": "me-2"}),
        initial="basic",
    )

    def clean(self):
        data = self.cleaned_data
        min_users = 1

        if data["num_users"] < min_users:
            raise ValidationError("Cannot create less than 1 users!")
