# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2023 Colin B. Macdonald

from django.urls import path

from . import views


# TODO: Document the API here? Sphinx best practices?

urlpatterns = [
    path("", views.SpecEditorView.as_view(), name="creator_launch"),
    path("text-editor", views.SpecEditorTextArea.as_view(), name="spec_text_edit"),
    path("summary", views.TestSpecSummaryView.as_view(), name="spec_summary"),
]
