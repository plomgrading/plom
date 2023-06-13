# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Edith Coates
# Copyright (C) 2023 Julian Lapenna
# Copyright (C) 2023 Divy Patel

from django.urls import path

from Rubrics import views


urlpatterns = [
    path("", views.RubricLandingPageView.as_view(), name="rubrics_landing"),
    path("<int:rubric_key>/", views.RubricItemView.as_view(), name="rubric_item"),
    path("<int:rubric_key>/edit/", views.RubricItemView.post, name="rubric_edit"),
]
