# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates

from django.contrib import admin

from Mark.models import MarkingTask, ClaimMarkingTask


# Register your models here.
admin.site.register(MarkingTask)
admin.site.register(ClaimMarkingTask)
