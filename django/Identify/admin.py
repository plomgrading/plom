# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates

from django.contrib import admin

from Identify.models import (
    PaperIDTask,
    PaperIDAction,
)

# Register your models here.
admin.site.register(PaperIDTask)
admin.site.register(PaperIDAction)
