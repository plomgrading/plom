# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2023 Colin B. Macdonald

from django.contrib import admin

from .models import (
    PaperIDTask,
    PaperIDAction,
    IDPrediction,
)

# This makes models appear in the admin interface
admin.site.register(PaperIDTask)
admin.site.register(PaperIDAction)
admin.site.register(IDPrediction)
