# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2022 Brennen Chiu

from urllib.parse import urlparse
from django.urls import path

from API.views import InfoSpec


urlpatterns = [
    path("info/spec/", InfoSpec.as_view(), name="api_info_spec"),
]
