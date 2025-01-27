# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Brennen Chiu
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2023-2024 Colin B. Macdonald

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

from .choices import (
    USERNAME_CHOICES,
    USER_TYPE_WITH_MANAGER_CHOICES,
    USER_TYPE_WITHOUT_MANAGER_CHOICES,
)


class CreateUserForm(UserCreationForm):
    username = forms.CharField(max_length=40, help_text="Username")
    email = forms.EmailField(
        max_length=100,
        help_text="Email",
        required=False,
        widget=forms.EmailInput(attrs={"placeholder": "Optional"}),
    )

    user_types = forms.CharField(
        label="What user type would you like to create?",
        widget=forms.RadioSelect(
            choices=USER_TYPE_WITH_MANAGER_CHOICES, attrs={"class": "me-2"}
        ),
        initial="marker",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["password1"].required = False
        self.fields["password2"].required = False
        self.fields["password1"].widget.attrs["autocomplete"] = "off"
        self.fields["password2"].widget.attrs["autocomplete"] = "off"

    class Meta:
        model = User
        fields = ["username", "email"]


class CreateMultiUsersForm(forms.Form):
    num_users = forms.IntegerField(
        widget=forms.NumberInput(
            attrs={
                "class": "form-control mb-2",
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

    user_types = forms.CharField(
        label="What user type would you like to create?",
        widget=forms.RadioSelect(
            choices=USER_TYPE_WITHOUT_MANAGER_CHOICES, attrs={"class": "me-2"}
        ),
        initial="marker",
    )

    def clean(self):
        data = self.cleaned_data
        min_users = 1

        if data["num_users"] < min_users:
            raise ValidationError("Cannot create less than 1 users!")
