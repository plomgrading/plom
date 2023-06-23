# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Brennen Chiu
# Copyright (C) 2023 Colin B. Macdonald

from django.contrib import admin
from .models import Profile

# Register your models here.
admin.site.register(Profile)
