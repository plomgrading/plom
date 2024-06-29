# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Elisa Pan

from django.contrib import admin
from .models import TmpAbstractQuestion, PedagogyTag, QuestionTag

admin.site.register(PedagogyTag)
admin.site.register(TmpAbstractQuestion)
admin.site.register(QuestionTag)
