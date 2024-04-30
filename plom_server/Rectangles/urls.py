# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Andrew Rechnitzer
from django.urls import path

from .views import (
    RectangleHomeView,
    SelectRectangleView,
    ExtractedRectangleView,
    ZipExtractedRectangleView,
    GetIDBoxRectangleView,
)

urlpatterns = [
    path("", RectangleHomeView.as_view(), name="rectangle_home"),
    path(
        "select/<int:version>/<int:page>",
        SelectRectangleView.as_view(),
        name="select_rectangle",
    ),
    path(
        "extract/<int:paper>/<int:version>/<int:page>",
        ExtractedRectangleView.as_view(),
        name="extracted_rectangle",
    ),
    path(
        "zip/<int:version>/<int:page>",
        ZipExtractedRectangleView.as_view(),
        name="zip_rectangles",
    ),
    path("id_rectangle", GetIDBoxRectangleView.as_view(), name="get_id_box_rectangle"),
]
