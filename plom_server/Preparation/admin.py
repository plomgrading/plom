# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Andrew Rechnitzer
# Copyright (C) 2023 Colin B. Macdonald

from django.contrib import admin

from .models import StagingStudent

# This makes models appear in the admin interface
admin.site.register(StagingStudent)
