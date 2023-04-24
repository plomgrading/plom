# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Brennen Chiu

from django.contrib import admin

from Rubrics.models import Rubric, RubricPane


admin.site.register(Rubric)
admin.site.register(RubricPane)
