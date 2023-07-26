# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Andrew Rechnitzer
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2023 Colin B. Macdonald

from django.urls import path
from Papers.views import CreateTestPapers, TestPaperProgress


urlpatterns = [
    path("init/", CreateTestPapers.as_view(), name="create_papers"),
    path("progress/", TestPaperProgress.as_view(), name="papers_progress"),
]
