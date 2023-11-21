# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2022 Brennen Chiu
# Copyright (C) 2023 Colin B. Macdonald

from django.contrib import admin

from .models import BuildPaperPDFChore

# This makes models appear in the admin interface
admin.site.register(BuildPaperPDFChore)
