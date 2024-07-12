# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Elisa Pan

from django.urls import path
from .views import (
    QTagsLandingView,
    AddQuestionTagView,
    CreateTagView,
    DeleteTagView,
    EditTagView,
)

urlpatterns = [
    path("qtags/", QTagsLandingView.as_view(), name="qtags_landing"),
    path("add/", AddQuestionTagView.as_view(), name="add_question_tag"),
    path("create/", CreateTagView.as_view(), name="create_tag"),
    path("delete/", DeleteTagView.as_view(), name="delete_tag"),
    path("edit/", EditTagView.as_view(), name="edit_tag"),
]