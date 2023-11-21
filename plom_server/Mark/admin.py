# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2023 Colin Macdonald

from django.contrib import admin

from .models import (
    MarkingTask,
    MarkingTaskTag,
    Annotation,
    AnnotationImage,
)

# This makes models appear in the admin interface
admin.site.register(MarkingTask)
admin.site.register(Annotation)
admin.site.register(AnnotationImage)
admin.site.register(MarkingTaskTag)
