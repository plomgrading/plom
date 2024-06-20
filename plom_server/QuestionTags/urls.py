# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Elisa Pan

from django.urls import path
from . import views

urlpatterns = [
    path('qtags/', views.qtags_landing, name='qtags_landing'),
    path('add/', views.add_question_tag, name='add_question_tag'),
    path('create_tag/', views.create_tag, name='create_tag'),
]
