# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2022 Brennen Chiu
# Copyright (C) 2023-2025 Colin B. Macdonald
# Copyright (C) 2023 Julian Lapenna
# Copyright (C) 2024 Andrew Rechnitzer
# Copyright (C) 2024 Aden Chan

"""Plom Server Django URL Configuration."""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings


urlpatterns = [
    path("admin/", admin.site.urls),
    # contains all the url path from Authentication App
    path("", include("plom_server.Authentication.urls")),
    path("", include("plom_server.UserManagement.urls")),
    path("", include("plom_server.Profile.urls")),
    path("", include("plom_server.API.urls")),
    path("", include("plom_server.Base.urls")),
    path("create/", include("plom_server.Preparation.urls")),
    path("create/spec/", include("plom_server.SpecCreator.urls")),
    path("create/paperpdfs/", include("plom_server.BuildPaperPDF.urls")),
    path("scan/", include("plom_server.Scan.urls")),
    path("progress/", include("plom_server.Progress.urls")),
    path("rubrics/", include("plom_server.Rubrics.urls")),
    path("paper_tags/", include("plom_server.Tags.urls")),
    path("finish/", include("plom_server.Finish.urls")),
    path("reports/", include("plom_server.Reports.urls")),
    path("task_order/", include("plom_server.TaskOrder.urls")),
    path("rectangles/", include("plom_server.Rectangles.urls")),
    path("identify/", include("plom_server.Identify.urls")),
    path("questiontags/", include("plom_server.QuestionTags.urls")),
    path("question_clustering/", include("plom_server.QuestionClustering.urls")),
]

# If debugging/profiling using django-silk, need to add pattern, presumably
# not during production.  See https://github.com/jazzband/django-silk
if settings.PROFILER_SILK_ENABLED:
    urlpatterns += [path("silk/", include("silk.urls", namespace="silk"))]
