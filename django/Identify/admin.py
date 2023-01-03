# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates

from django.contrib import admin

from Identify.models import (
    PaperIDTask,
    PaperIDClaim,
    PaperIDAction,
    SurrenderPaperIDTask,
)

# Register your models here.
admin.site.register(PaperIDTask)
admin.site.register(PaperIDClaim)
admin.site.register(PaperIDAction)
admin.site.register(SurrenderPaperIDTask)
