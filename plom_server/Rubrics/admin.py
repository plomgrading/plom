# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Brennen Chiu
# Copyright (C) 2023 Colin B. Macdonald

from django.contrib import admin

from .models import Rubric, RubricPane

# This makes models appear in the admin interface
admin.site.register(Rubric)
admin.site.register(RubricPane)
