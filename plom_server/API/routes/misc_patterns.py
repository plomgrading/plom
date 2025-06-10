# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2022 Brennen Chiu
# Copyright (C) 2022-2023 Colin B. Macdonald
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2024-2025 Bryan Tanady
# Copyright (C) 2025 Philip D. Loewen

from django.urls import path

from ..views import (
    ExamInfo,
    ServerInfo,
    ServerVersion,
    CloseUser,
    UserRole,
    QuestionMaxMark,
    ObtainAuthTokenUpdateLastLogin,
    UsersInfo,
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
            path("info/users/", UsersInfo.as_view(), name="api_users_info"),
            path("info/user/<str:username>", UserRole.as_view(), name="api_user_role"),
            path(
                "maxmark/<int:question>",
                QuestionMaxMark.as_view(),
                name="api_question_mark",
            ),
        ]

        # Authentication and token handling
        misc_patterns += [
            path(
                "get_token/",
                ObtainAuthTokenUpdateLastLogin.as_view(),
                name="api_get_token",
            ),
            path("close_user/", CloseUser.as_view(), name="api_close_user"),
        ]

        return misc_patterns
