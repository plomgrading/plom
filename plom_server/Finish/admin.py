# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2022-2023 Brennen Chiu
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2023, 2025 Colin B. Macdonald

from django.contrib import admin

from .models import (
    BuildSolutionPDFChore,
    ReassemblePaperChore,
    SolutionImage,
    SolutionSourcePDF,
)

# This makes models appear in the admin interface
admin.site.register(BuildSolutionPDFChore)
admin.site.register(ReassemblePaperChore)
admin.site.register(SolutionImage)
admin.site.register(SolutionSourcePDF)
