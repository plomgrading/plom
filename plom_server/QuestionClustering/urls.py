# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Bryan Tanady

from django.urls import path

from .views import QuestionClusteringHomeView, SelectRectangleForClusteringView

urlpatterns = [
    path("", QuestionClusteringHomeView.as_view(), name="question_clustering_home"),
    path(
        "select/<int:version>/<int:qidx>/<int:page>",
        SelectRectangleForClusteringView.as_view(),
        name="question_clustering_select_rectangle",
    ),
]
