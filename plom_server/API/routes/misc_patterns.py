# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2022 Brennen Chiu
# Copyright (C) 2022-2023 Colin B. Macdonald

from django.urls import path
from rest_framework.authtoken.views import obtain_auth_token

from ..views import (
    ExamInfo,
    GetSpecification,
    ServerInfo,
    ServerVersion,
    CloseUser,
    QuestionMaxMark,
)


class MiscURLPatterns:
    """URL patterns that don't fit in the other files.

    All of these patterns have no particular prefix.
    """

    @classmethod
    def patterns(cls):
        misc_patterns = [
            path("Version/", ServerVersion.as_view(), name="api_server_version"),
            path("info/server/", ServerInfo.as_view(), name="api_server_info"),
            path("info/exam/", ExamInfo.as_view(), name="api_exam_info"),
            path("info/spec/", GetSpecification.as_view(), name="api_info_spec"),
            path(
                "maxmark/<int:question>",
                QuestionMaxMark.as_view(),
                name="api_question_mark",
            ),
        ]

        # Authentication and token handling
        misc_patterns += [
            path("get_token/", obtain_auth_token, name="api_get_token"),
            path("close_user/", CloseUser.as_view(), name="api_close_user"),
        ]

        return misc_patterns
