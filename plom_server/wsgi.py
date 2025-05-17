# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Brennen Chiu
# Copyright (C) 2023, 2025 Colin B. Macdonald

"""WSGI config for the Plom Server project."""

import os

from django.core.wsgi import get_wsgi_application
from whitenoise import WhiteNoise

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "plom_server.settings")

application = get_wsgi_application()
application = WhiteNoise(application)
