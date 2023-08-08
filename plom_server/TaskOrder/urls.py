# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Julian Lapenna

from django.urls import path

from .views import TaskOrderPageView


urlpatterns = [
    path("", TaskOrderPageView.as_view(), name="task_order_landing"),
    path(
        "upload_task_priorities/",
        TaskOrderPageView.upload_task_priorities,
        name="upload_task_priorities",
    ),
    path(
        "download_priorities/",
        TaskOrderPageView.download_priorities,
        name="download_priorities",
    ),
]
