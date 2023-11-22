# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Brennen Chiu
# Copyright (C) 2023 Colin Macdonald

from django.contrib import admin

from .models import HueyTaskTracker

# This makes models appear in the admin interface
admin.site.register(HueyTaskTracker)
