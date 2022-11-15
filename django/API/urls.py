# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2022 Brennen Chiu

from django.urls import path
from rest_framework.authtoken.views import obtain_auth_token

from API.views import (
    GetSpecification,
    ServerVersion,
    QuestionMaxMark,
    QuestionMaxMark2,
    GetClasslist,
    GetIDPredictions,
)


urlpatterns = [
    path("info/spec/", GetSpecification.as_view(), name="api_info_spec"),
    path("Version/", ServerVersion.as_view(), name="api_server_version"),
    path("MK/maxMark/", QuestionMaxMark.as_view(), name="api_question_mark"),
    path("maxmark/<int:question>", QuestionMaxMark2.as_view(), name="api_question_mark2"),
    path("ID/classlist/", GetClasslist.as_view(), name="api_get_classlist"),
    path("ID/predictions/", GetIDPredictions.as_view(), name="api_get_predictions"),
]

urlpatterns += [
    path("get_token/", obtain_auth_token, name="api_get_token"),
]
