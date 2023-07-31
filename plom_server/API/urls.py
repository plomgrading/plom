# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Edith Coates
# Copyright (C) 2023 Colin B. Macdonald

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from API.views.experimental import (
    RubricViewSet,
    AnnotationViewSet,
    MarkingTaskViewSet,
)

from API.routes import (
    MarkURLPatterns,
    IdURLPatterns,
    PagedataPatterns,
    AnnotationPatterns,
    AnnotationImagePatterns,
    MiscURLPatterns,
    TagsURLPatterns,
)

# TODO: these are possibly temporary
from API.views import (
    REPspreadsheet,
    REPidentified,
    REPcompletionStatus,
    REPcoverPageInfo,
)

"""
Handle URL patterns for the plom-client / server API.
See docs for including other URLconfs:
https://docs.djangoproject.com/en/4.2/topics/http/urls/#including-other-urlconfs

Note: The URL Patterns classes are made in order to seamlessly split up urls.py
across multiple files. In the future, once we're able to start changing the design
of the plom-client URLS, we ought to transition to using Django REST Framework
routers: https://www.django-rest-framework.org/api-guide/routers/
"""


urlpatterns = [
    path("", include(MiscURLPatterns.patterns())),
    path(MarkURLPatterns.prefix, include(MarkURLPatterns.patterns())),
    path(IdURLPatterns.prefix, include(IdURLPatterns.patterns())),
    path(PagedataPatterns.prefix, include(PagedataPatterns.patterns())),
    path(AnnotationPatterns.prefix, include(AnnotationPatterns.patterns())),
    path(AnnotationImagePatterns.prefix, include(AnnotationImagePatterns.patterns())),
    path(TagsURLPatterns.prefix, include(TagsURLPatterns.patterns())),
    path(
        "REP/spreadsheet",
        REPspreadsheet.as_view(),
        name="api_REP_spreadsheet",
    ),
    path(
        "REP/identified",
        REPidentified.as_view(),
        name="api_REP_identified",
    ),
    path(
        "REP/completionStatus",
        REPcompletionStatus.as_view(),
        name="api_REP_completion_status",
    ),
    path(
        "REP/coverPageInfo/<int:papernum>",
        REPcoverPageInfo.as_view(),
        name="api_REP_cover_page_info",
    ),
]

experimental_router = DefaultRouter(trailing_slash=True)
experimental_router.register("rubrics", RubricViewSet, basename="rubrics")
experimental_router.register("annotations", AnnotationViewSet, basename="annotations")
experimental_router.register(
    "marking-tasks", MarkingTaskViewSet, basename="marking-tasks"
)

urlpatterns += [path("experimental/", include(experimental_router.urls))]
