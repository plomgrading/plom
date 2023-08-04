# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2023 Colin B. Macdonald

from django.contrib import admin

from . import models


# Register your models here.
admin.site.register(models.ReferencePDF)
admin.site.register(models.TestSpecInfo)
admin.site.register(models.TestSpecQuestion)
admin.site.register(models.StagingSpecification)
