# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Brennen Chiu
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2023-2026 Colin B. Macdonald
# Copyright (C) 2024, 2026 Aidan Murphy

from django.urls import path

from .signup_views import (
    ImportUsers,
    ImportUsersCreation,
    MultiUsersSignUp,
    MultiUsersCreation,
    SingleUserSignUp,
    SingleUserCreation,
)
from .views import (
    LoginView,
    LogoutView,
    SetPassword,
)

urlpatterns = [
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("signup/single/", SingleUserSignUp.as_view(), name="signup_single"),
    path(
        "signup/single/create", SingleUserCreation.as_view(), name="create_single_user"
    ),
    path("signup/multiple/", MultiUsersSignUp.as_view(), name="signup_multiple"),
    path(
        "signup/multiple/create",
        MultiUsersCreation.as_view(),
        name="create_multiple_users",
    ),
    path("signup/import/", ImportUsers.as_view(), name="signup_import"),
    path(
        "signup/import/create",
        ImportUsersCreation.as_view(),
        name="create_import_users",
    ),
    path(
        "reset/<slug:uidb64>/<slug:token>/",
        SetPassword.as_view(),
        name="password_reset",
    ),
]
