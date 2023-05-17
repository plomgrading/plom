# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Edith Coates

from django.urls import path

from API.views import (
    TagsFromCodeView,
    GetAllTags,
)


class TagsURLPatterns:
    """
    URLs for handling marking task-related tags.
    """

    prefix = "tags/"

    @staticmethod
    def get_patterns():
        tag_patterns = [
            path("", GetAllTags.as_view(), name="api_all_tags"),
            path("<code>", TagsFromCodeView.as_view(), name="api_tags_code"),
        ]

        return tag_patterns

    patterns = get_patterns()
