# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2022 Brennen Chiu
# Copyright (C) 2022-2023 Colin B. Macdonald

from django.urls import path, re_path
from rest_framework.authtoken.views import obtain_auth_token

from API.views import (
    GetSpecification,
    ServerVersion,
    CloseUser,
    QuestionMaxMark_how_to_get_data,
    QuestionMaxMark,
    GetClasslist,
    GetIDPredictions,
    IDgetDoneTasks,
    IDgetNextTask,
    IDprogressCount,
    IDclaimThisTask,
    IDgetImage,
    MarkingProgressCount,
    MgetNextTask,
    MclaimThisTask,
    MgetQuestionPageData,
    MgetOneImage,
    MgetAnnotations,
    MgetAnnotationImage,
    MgetRubricsByQuestion,
    MgetRubricPanes,
    McreateRubric,
    MmodifyRubric,
    MlatexFragment,
)


# TODO: are any of these authenticated?  How do we decorate or otherwise implement
# and indicate that?  See @write_admin, @readonly_admin in the legacy server.


urlpatterns = [
    path("info/spec/", GetSpecification.as_view(), name="api_info_spec"),
    path("Version/", ServerVersion.as_view(), name="api_server_version"),
    path(
        "MK/maxMark/",
        QuestionMaxMark_how_to_get_data.as_view(),
        name="api_question_mark_TODO",
    ),
    path("maxmark/<int:question>", QuestionMaxMark.as_view(), name="api_question_mark"),
    path("ID/classlist/", GetClasslist.as_view(), name="api_get_classlist"),
    path("ID/predictions/", GetIDPredictions.as_view(), name="api_get_predictions"),
    path("ID/tasks/complete", IDgetDoneTasks.as_view(), name="api_ID_get_done_tasks"),
    path("ID/tasks/available", IDgetNextTask.as_view(), name="api_ID_get_next_tasks"),
    path("MK/tasks/complete", IDgetDoneTasks.as_view(), name="api_MK_get_done_tasks"),
    path("MK/tasks/available", MgetNextTask.as_view(), name="api_MK_get_next_tasks"),
    path("ID/progress", IDprogressCount.as_view(), name="api_ID_progress_count"),
    path(
        "MK/progress", MarkingProgressCount.as_view(), name="api_marking_progress_count"
    ),
    path("MK/tasks/<code>", MclaimThisTask.as_view(), name="api_MK_claim_task"),
    path("ID/tasks/<paper_id>", IDclaimThisTask.as_view(), name="api_ID_claim_task"),
    path(
        "pagedata/<int:paper>/context/<int:question>",
        MgetQuestionPageData.as_view(),
        name="api_question_data",
    ),
    path("MK/images/<int:pk>/<hash>/", MgetOneImage.as_view(), name="api_MK_one_image"),
    path("ID/image/<paper_id>/", IDgetImage.as_view(), name="api_ID_get_image"),
    path(
        "annotations/<int:paper>/<int:question>/",
        MgetAnnotations.as_view(),
        name="api_MK_annotation",
    ),
    path(
        "annotations_image/<int:paper>/<int:question>/",
        MgetAnnotationImage.as_view(),
        name="api_MK_annotation_img",
    ),
    re_path(
        r"MK/rubric/(?P<question>[0-9]{,5})$",
        MgetRubricsByQuestion.as_view(),
        name="api_MK_get_rubric",
    ),
    path(
        "MK/user/<username>/<int:question>",
        MgetRubricPanes.as_view(),
        name="api_MK_get_rubric_panes",
    ),
    path("MK/rubric", McreateRubric.as_view(), name="api_MK_create_rubric"),
    re_path(
        r"MK/rubric/(?P<key>[0-9]{12})$",
        MmodifyRubric.as_view(),
        name="api_MK_modify_rubric",
    ),
    path(
        "MK/latex",
        MlatexFragment.as_view(),
        name="api_MK_latex_fragment",
    ),
]

urlpatterns += [
    path("get_token/", obtain_auth_token, name="api_get_token"),
    path("close_user/", CloseUser.as_view(), name="api_close_user"),
]
