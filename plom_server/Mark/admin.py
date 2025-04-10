# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2023, 2025 Colin Macdonald

from django.contrib import admin

from .models import (
    Annotation,
    AnnotationImage,
    MarkingTask,
    MarkingTaskPriority,
    MarkingTaskTag,
)

# This makes models appear in the admin interface
admin.site.register(Annotation)
admin.site.register(AnnotationImage)
admin.site.register(MarkingTask)
admin.site.register(MarkingTaskPriority)
admin.site.register(MarkingTaskTag)
