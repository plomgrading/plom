# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Brennen Chiu
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2023, 2025 Colin B. Macdonald

"""ASGI config for the Plom Server project."""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")

application = get_asgi_application()
