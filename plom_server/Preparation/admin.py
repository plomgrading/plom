# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Andrew Rechnitzer
# Copyright (C) 2023, 2025 Colin B. Macdonald

from django.contrib import admin

from .models import (
    PaperSourcePDF,
    PapersPrintedSettingModel,
    PrenamingSetting,
    StagingPQVMapping,
    StagingStudent,
)

# This makes models appear in the admin interface
admin.site.register(PaperSourcePDF)
admin.site.register(PapersPrintedSettingModel)
admin.site.register(PrenamingSetting)
admin.site.register(StagingPQVMapping)
admin.site.register(StagingStudent)
