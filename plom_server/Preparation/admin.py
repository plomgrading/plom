# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Andrew Rechnitzer
# Copyright (C) 2023 Colin B. Macdonald

from django.contrib import admin
from .models import StagingStudent


# Register your models here.
admin.site.register(StagingStudent)
