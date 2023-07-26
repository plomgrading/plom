# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates

from django.contrib import admin

from Identify.models import (
    PaperIDTask,
    PaperIDAction,
    IDPrediction,
)

# Register your models here.
admin.site.register(PaperIDTask)
admin.site.register(PaperIDAction)
admin.site.register(IDPrediction)
