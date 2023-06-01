# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Edith Coates
# Copyright (C) 2023 Julian Lapenna

from django.urls import path

from Rubrics import views


urlpatterns = [
    path(
        "", 
        views.RubricLandingPageView.as_view(), 
        name="rubrics_landing"
        ),
    path("select/",  
        views.RubricLandingPageView.select,
        name="select"),
]
