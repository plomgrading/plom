# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Edith Coates
# Copyright (C) 2023 Julian Lapenna
# Copyright (C) 2023 Divy Patel
# Copyright (C) 2024 Colin B. Macdonald

from django.urls import path

from . import views


urlpatterns = [
    path("", views.RubricLandingPageView.as_view(), name="rubrics_landing"),
    path("admin/", views.RubricAdminPageView.as_view(), name="rubrics_admin"),
    path("admin/wipe/", views.RubricWipePageView.as_view(), name="rubrics_wipe"),
    path("admin/access/", views.RubricAccessPageView.as_view(), name="rubrics_access"),
    path(
        "admin/annotation_situations/",
        views.RubricAnnotationSituationsView.as_view(),
        name="rubrics_annotation_situations",
    ),
    path("<int:rubric_key>/", views.RubricItemView.as_view(), name="rubric_item"),
    path("<int:rubric_key>/edit/", views.RubricItemView.post, name="rubric_edit"),
]
