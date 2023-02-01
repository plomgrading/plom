# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates

from django.contrib import admin

from Mark.models import (
    MarkingTask,
    ClaimMarkingTask,
    SurrenderMarkingTask,
    MarkAction,
    Annotation,
    AnnotationImage,
)


# Register your models here.
admin.site.register(MarkingTask)
admin.site.register(ClaimMarkingTask)
admin.site.register(SurrenderMarkingTask)
admin.site.register(MarkAction)
admin.site.register(Annotation)
admin.site.register(AnnotationImage)
