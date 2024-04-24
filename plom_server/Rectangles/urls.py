# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Andrew Rechnitzer
from django.urls import path

from .views import RectangleHomeView, SelectRectangleView

urlpatterns = [
    path("", RectangleHomeView.as_view(), name="rectangle_home"),
    path(
        "select/<int:version>/<int:page>",
        SelectRectangleView.as_view(),
        name="select_rectangle",
    ),
]
