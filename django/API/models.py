# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2022 Brennen Chiu

from django.db import models
from django.contrib.auth.models import User


class NumberToIncrement(models.Model):
    """
    A proof-of-concept: increment a number from an outside client
    using our authentication system
    """

    number = models.IntegerField(default=0)
    user = models.OneToOneField(User, on_delete=models.SET_NULL, null=True)
