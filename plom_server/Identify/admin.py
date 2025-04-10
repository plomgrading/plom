# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2023, 2025 Colin B. Macdonald

from django.contrib import admin

from .models import (
    IDPrediction,
    IDReadingHueyTaskTracker,
    IDRectangle,
    PaperIDAction,
    PaperIDTask,
)

# This makes models appear in the admin interface
admin.site.register(IDPrediction)
admin.site.register(IDReadingHueyTaskTracker)
admin.site.register(IDRectangle)
admin.site.register(PaperIDAction)
admin.site.register(PaperIDTask)
