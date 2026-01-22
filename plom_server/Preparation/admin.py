# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Andrew Rechnitzer
# Copyright (C) 2023, 2025 Colin B. Macdonald
# Copyright (C) 2026 Aidan Murphy

from django.contrib import admin

from .models import (
    PaperSourcePDF,
    StagingStudent,
)

# This makes models appear in the admin interface
admin.site.register(PaperSourcePDF)
admin.site.register(StagingStudent)
