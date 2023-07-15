# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Brennen Chiu

from django.contrib.auth.forms import UserChangeForm
from django.contrib.auth.models import User


class EditProfileForm(UserChangeForm):
    class Meta:
        model = User
        fields = ["first_name", "email"]
