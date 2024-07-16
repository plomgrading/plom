# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Elisa Pan

from django.contrib import admin
from .models import TmpAbstractQuestion, PedagogyTag, QuestionTagLink


class QuestionTagInline(admin.TabularInline):
    """Inline admin class to manage the relationship between questions and tags.

    This class allows the admin to manage QuestionTagLink objects directly
    from the TmpAbstractQuestion admin page.
    """

    model = QuestionTagLink
    extra = 1


@admin.register(TmpAbstractQuestion)
class TmpAbstractQuestionAdmin(admin.ModelAdmin):
    """Admin class for TmpAbstractQuestion model.

    This class customizes the admin interface for TmpAbstractQuestion objects,
    including inline editing of related QuestionTagLink objects and displaying
    the question_index field in the list view.
    """

    inlines = [QuestionTagInline]
    list_display = ["question_index"]


admin.site.register(PedagogyTag)
admin.site.register(QuestionTagLink)
