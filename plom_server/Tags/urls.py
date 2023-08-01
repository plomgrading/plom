# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Julian Lapenna

from django.urls import path

from .views import TagLandingPageView, TagItemView


urlpatterns = [
    path("", TagLandingPageView.as_view(), name="tags_landing"),
    path("tag_filter/", TagLandingPageView.tag_filter, name="tag_filter"),
    path("<int:tag_id>/item/", TagItemView.as_view(), name="tag_item"),
    path("<int:tag_id>/edit/", TagItemView.post, name="tag_edit"),
    path("<int:tag_id>/tag_delete/", TagItemView.tag_delete, name="tag_delete"),
]
