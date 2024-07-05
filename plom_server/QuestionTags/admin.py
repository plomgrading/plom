# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Elisa Pan

from django.contrib import admin
from .models import TmpAbstractQuestion, PedagogyTag, QuestionTagLink


class QuestionTagInline(admin.TabularInline):
    model = QuestionTagLink
    extra = 1


@admin.register(TmpAbstractQuestion)
class TmpAbstractQuestionAdmin(admin.ModelAdmin):
    inlines = [QuestionTagInline]
    list_display = ["question_index"]


admin.site.register(PedagogyTag)
admin.site.register(QuestionTagLink)
