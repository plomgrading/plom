# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Edith Coates
# Copyright (C) 2023-2024 Colin B. Macdonald

from django.urls import include, path
from rest_framework.routers import DefaultRouter, SimpleRouter

from .views.experimental import (
    RubricViewSet,
    AnnotationViewSet,
    MarkingTaskViewSet,
)

from .routes import (
    MarkURLPatterns,
    IdURLPatterns,
    PagedataPatterns,
    AnnotationPatterns,
    AnnotationImagePatterns,
    MiscURLPatterns,
    TagsURLPatterns,
)

from .views import (
    QuestionMarkingViewSet,
    # TODO: these are possibly temporary
    REPspreadsheet,
    REPidentified,
    REPcompletionStatus,
    REPcoverPageInfo,
)

from .views.rubrics import MgetRubricMarkingTasks

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

marking_router = SimpleRouter(trailing_slash=False)
marking_router.register("tasks", QuestionMarkingViewSet, basename="tasks")

urlpatterns += [
    path("experimental/", include(experimental_router.urls)),
    path("MK/", include(marking_router.urls)),
    path(
        "rubrics/<str:int/tasks",
        MgetRubricMarkingTasks.as_view(),
        name="api_rubrics_tasks",
    ),
]
