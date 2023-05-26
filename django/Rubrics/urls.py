# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Edith Coates

from django.urls import path

from Rubrics.views import RubricLandingPageView


urlpatterns = [path("", RubricLandingPageView.as_view(), name="rubrics_landing")]
