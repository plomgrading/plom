# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Brennen Chiu
# Copyright (C) 2023, 2025 Colin Macdonald
# Copyright (C) 2025 Andrew Rechnitzer

from django.contrib import admin

from .models import BaseImage, HueyTaskTracker, SettingsModel

# This makes models appear in the admin interface
admin.site.register(BaseImage)
admin.site.register(HueyTaskTracker)
admin.site.register(SettingsModel)
