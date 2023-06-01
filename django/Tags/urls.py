# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Julian Lapenna

from django.urls import path

from Tags.views import TagLandingPageView


urlpatterns = [path("", TagLandingPageView.as_view(), name="tags_landing")]