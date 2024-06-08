# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Elisa Pan

from django.urls import path
from . import views

urlpatterns = [
    path('qtags/', views.qtags_landing, name='qtags_landing'),
]