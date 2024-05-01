# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Andrew Rechnitzer
from django.urls import path

from .views import (
    GetIDBoxRectangleView,
)

urlpatterns = [
    path("id_rectangle", GetIDBoxRectangleView.as_view(), name="get_id_box_rectangle"),
]
