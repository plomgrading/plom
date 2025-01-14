# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Brennen Chiu
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2023-2025 Colin B. Macdonald
# Copyright (C) 2024 Aidan Murphy

from django.urls import path

from .signup_views import (
    ImportUsers,
    MultiUsersSignUp,
    SingleUserSignUp,
)
from .views import (
    Home,
    LoginView,
    LogoutView,
    Maintenance,
    SetPassword,
    SetPasswordComplete,
)

urlpatterns = [
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("", Home.as_view(), name="home"),
    path("maintenance/", Maintenance.as_view(), name="maintenance"),
    path("signup/single/", SingleUserSignUp.as_view(), name="signup_single"),
    path("signup/multiple/", MultiUsersSignUp.as_view(), name="signup_multiple"),
    path("signup/import/", ImportUsers.as_view(), name="signup_import"),
    path(
        "reset/<slug:uidb64>/<slug:token>/",
        SetPassword.as_view(),
        name="password_reset",
    ),
    path("reset/done/", SetPasswordComplete.as_view(), name="password_reset_complete"),
]
