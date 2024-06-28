# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Elisa Pan

from django.contrib import admin
from .models import QuestionTag, PedagogyTag

admin.site.register(PedagogyTag)
admin.site.register(QuestionTag)
