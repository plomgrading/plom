# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Brennen Chiu
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2023-2024 Colin B. Macdonald
# Copyright (C) 2025 Andrew Rechnitzer

from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

from .choices import (
    USERNAME_CHOICES,
    USER_TYPE_WITH_MANAGER_CHOICES,
    USER_TYPE_WITHOUT_MANAGER_CHOICES,
)


class CreateSingleUserForm(forms.ModelForm):
    username = forms.CharField(max_length=150, help_text="Username")
    # we set max length here because by default CharField is length unlimited, but
    # in the User object from django-auth, the field is limited to 150
    # https://docs.djangoproject.com/en/5.0/ref/contrib/auth/#django.contrib.auth.models.User.username
    # see above - default max length of username in django is 150.
    email = forms.EmailField(
        help_text="Email",
        required=False,
        widget=forms.EmailInput(attrs={"placeholder": "Optional"}),
    )
    # do not set length on emailfield - django default is 254.
    # https://docs.djangoproject.com/en/5.0/ref/models/fields/#django.db.models.CharField

    user_types = forms.CharField(
        label="What user type would you like to create?",
        widget=forms.RadioSelect(
            choices=USER_TYPE_WITH_MANAGER_CHOICES, attrs={"class": "me-2"}
        ),
        initial="marker",
    )

    class Meta:
        model = User
        fields = ["username", "email"]

    def clean_username(self):
        """Reject usernames that differ only in case."""
        # we no longer subclass UserCreationForm (Issue #3798) so instead we implement username
        # cleaning following Django's UserCreationForm
        # https://github.com/django/django/blob/stable/5.1.x/django/contrib/auth/forms.py#L221
        username = self.cleaned_data.get("username")
        # TODO - do we want other username checks? they should prolly go here.
        if (
            username
            and self._meta.model.objects.filter(username__iexact=username).exists()
        ):
            self._update_errors(
                ValidationError(
                    {
                        "username": self.instance.unique_error_message(
                            self._meta.model, ["username"]
                        )
                    }
                )
            )
        else:
            return username


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
        if data["num_users"] < 1:
            raise ValidationError("Cannot create fewer than 1 users!")
        return self.super().clean()
