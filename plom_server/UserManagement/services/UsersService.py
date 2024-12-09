# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Colin B. Macdonald
# Copyright (C) 2024 Aidan Murphy

from django.contrib.auth.models import User


# TODO: can probably do this in one call
def get_user_info() -> dict:
    users = {
        "managers": User.objects.filter(groups__name="manager"),
        "scanners": User.objects.filter(groups__name="scanner").exclude(
            groups__name="manager"
        ),
        "lead_markers": User.objects.filter(groups__name="lead_marker"),
        "markers": User.objects.filter(groups__name="marker").prefetch_related(
            "auth_token"
        ),
    }
    return users
