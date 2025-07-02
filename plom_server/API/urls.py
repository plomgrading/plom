# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Edith Coates
# Copyright (C) 2023-2025 Colin B. Macdonald
# Copyright (C) 2025 Philip D. Loewen
# Copyright (C) 2025 Aidan Murphy

from django.urls import include, path, re_path
from rest_framework.routers import DefaultRouter

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
    ClasslistHandler,
    GetTasks,
    MarkTaskNextAvailable,
    MarkTask,
    ReassignTask,
    ResetTask,
    # TODO: these are possibly temporary
    papersToPrint,
    ScanListBundles,
    ScanBundleActions,
    ScanMapBundle,
    FinishReassembled,
    FinishUnmarked,
    REPspreadsheet,
    REPidentified,
    REPcompletionStatus,
    REPcoverPageInfo,
    SourceOverview,
    SourceDetail,
    SpecificationHandler,
)

from .views import MgetRubricMarkingTasks

"""
Handle URL patterns for the plom-client / server API.
See docs for including other URLconfs:
https://docs.djangoproject.com/en/4.2/topics/http/urls/#including-other-urlconfs

Note: The URL Patterns classes are made in order to split up urls.py
across multiple files.  These files are found in routes/

Note: In the future, we might consider transitioning to using Django REST Framework
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
    # TODO: Issue #3786: eventually remove the "beta" from these provisional URLs
    path(
        "api/beta/paperstoprint",
        papersToPrint.as_view(),
        name="papersToPrint",
    ),
    path(
        "api/beta/paperstoprint/<int:papernumber>",
        papersToPrint.as_view(),
        name="papersToPrint-withint",
    ),
    path(
        "api/beta/paperstoprint/<str:action>",
        papersToPrint.as_view(),
        name="papersToPrint-withstr",
    ),
    path(
        "api/beta/scan/bundles",
        ScanListBundles.as_view(),
        name="api_Scan_bundles",
    ),
    path(
        "api/beta/scan/bundle/<int:bundle_id>",
        ScanBundleActions.as_view(),
        name="api_can_bundle_actions",
    ),
    # "api/beta/scan/bundle/<int:bundle_id>/map/<int:papernum>/<str:questions>",
    path(
        "api/beta/scan/bundle/<int:bundle_id>/<int:page>/map",
        ScanMapBundle.as_view(),
        name="api_Scan_bundle_map",
    ),
    path(
        "api/beta/finish/reassembled/<int:papernum>",
        FinishReassembled.as_view(),
        name="api_Finish_reassembled",
    ),
    path(
        "api/beta/finish/unmarked/<int:papernum>",
        FinishUnmarked.as_view(),
        name="api_Finish_unmarked",
    ),
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
    path(
        "api/v0/spec",
        SpecificationHandler.as_view(),
        name="api_spec_handler",
    ),
    # Django inspects patterns in order, using the first match.
    # So the more specific one should appear first, as shown here.
    path(
        "api/v0/source/<int:version>",
        SourceDetail.as_view(),
        name="api_source_detail",
    ),
    path(
        "api/v0/source",
        SourceOverview.as_view(),
        name="api_source_overview",
    ),
]

experimental_router = DefaultRouter(trailing_slash=True)
experimental_router.register("rubrics", RubricViewSet, basename="rubrics")
experimental_router.register("annotations", AnnotationViewSet, basename="annotations")
experimental_router.register(
    "marking-tasks", MarkingTaskViewSet, basename="marking-tasks"
)

urlpatterns += [
    path("experimental/", include(experimental_router.urls)),
    # Note: other MK/ paths are in routes/mark_patterns.py
    path(
        "MK/tasks/available", MarkTaskNextAvailable.as_view(), name="api_mark_task_next"
    ),
    path("MK/tasks/all", GetTasks.as_view(), name="api_MK_get_tasks_all"),
    re_path("MK/tasks/(?P<code>q.+)", MarkTask.as_view(), name="api_mark_task"),
    path(
        "api/v0/tasks/<int:papernum>/<int:qidx>/reassign/<str:new_username>",
        ReassignTask.as_view(),
        name="api_task_reassign_new_username",
    ),
    path(
        "api/v0/tasks/<int:papernum>/<int:qidx>/reset",
        ResetTask.as_view(),
        name="api_task_reset",
    ),
    path(
        "api/v0/classlist",
        ClasslistHandler.as_view(),
        name="api_classlist_handler",
    ),
    path(
        "rubrics/<int:rid>/tasks",
        MgetRubricMarkingTasks.as_view(),
        name="api_rubrics_tasks",
    ),
]
