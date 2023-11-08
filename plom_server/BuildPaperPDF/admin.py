# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2022 Brennen Chiu

from django.contrib import admin
from .models import PDFHueyTask

# Register your models here.
admin.site.register(PDFHueyTask)
