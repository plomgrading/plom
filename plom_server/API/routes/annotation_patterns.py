# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2022 Brennen Chiu
# Copyright (C) 2022-2024 Colin B. Macdonald

from django.urls import path

from ..views import (
    MgetPageDataQuestionInContext,
    MgetAnnotations,
    MgetAnnotationImage,
)

"""URLs for handling annotation data."""


class PagedataPatterns:
    """Data for creating annotation images from pages.

    These patterns fall under the route "pagedata".
    """

    prefix = "pagedata/"

    # GET: /pagedata/{papernum}
    # GET: /pagedata/{papernum}/context/{questionidx}
    @classmethod
    def patterns(cls):
        pagedata_patterns = [
            path(
                "<int:papernum>",
                MgetPageDataQuestionInContext.as_view(),
                name="api_pagedata",
            ),
            path(
                "<int:papernum>/context/<int:questionidx>",
                MgetPageDataQuestionInContext.as_view(),
                name="api_pagedata_context_question",
            ),
        ]

        return pagedata_patterns


class AnnotationPatterns:
    """URLs for getting annotations.

    These patterns fall under the route "annotations"
    """

    prefix = "annotations/"

    @classmethod
    def patterns(cls):
        annotations_patterns = [
            path(
                "<int:paper>/<int:question>/",
                MgetAnnotations.as_view(),
                name="api_MK_annotation",
            ),
        ]

        return annotations_patterns


class AnnotationImagePatterns:
    """URLs for annotation images.

    These patterns fall under the route "annotations_image"
    """

    prefix = "annotations_image/"

    @classmethod
    def patterns(cls):
        annotations_image_patterns = [
            path(
                "<int:paper>/<int:question>/<int:edition>",
                MgetAnnotationImage.as_view(),
                name="api_MK_annotation_img_with_edition",
            ),
            path(
                "<int:paper>/<int:question>",
                MgetAnnotationImage.as_view(),
                name="api_MK_annotation_img",
            ),
        ]

        return annotations_image_patterns
