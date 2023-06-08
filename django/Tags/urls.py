# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Julian Lapenna

from django.urls import path

from Tags.views import TagLandingPageView, TagItemView


urlpatterns = [
    path("", TagLandingPageView.as_view(), name="tags_landing"),
    path("tag_filter/", TagLandingPageView.tag_filter, name="tag_filter"),
    path("<str:tag_text>/item/", TagItemView.as_view(), name="tag_item"),
    path("<str:tag_text>/edit/", TagItemView.post, name="tag_edit"),
    path("<str:tag_text>/tag_delete/", TagItemView.tag_delete, name="tag_delete"),
]
