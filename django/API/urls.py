# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2022 Brennen Chiu
# Copyright (C) 2022 Colin B. Macdonald

from django.urls import path
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
    MgetNextTask,
    MclaimThisTask,
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
    path("MK/progress", IDprogressCount.as_view(), name="api_ID_progress_count"),
    path("MK/tasks/<code>", MclaimThisTask.as_view(), name="api_MK_claim_task"),
]

urlpatterns += [
    path("get_token/", obtain_auth_token, name="api_get_token"),
    path("close_user/", CloseUser.as_view(), name="api_close_user"),
]
