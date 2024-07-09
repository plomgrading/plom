# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2024 Andrew Rechnitzer
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2023 Colin B. Macdonald

from django.urls import path
from Papers.views import CreateTestPapers


urlpatterns = [
    path("init/", CreateTestPapers.as_view(), name="create_papers"),
]
