# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Colin B. Macdonald

from django.contrib.auth.models import User


def get_user_info() -> list:
    managers = User.objects.filter(groups__name="manager")
    scanners = User.objects.filter(groups__name="scanner").exclude(
        groups__name="manager"
    )
    lead_markers = User.objects.filter(groups__name="lead_marker")
    markers = User.objects.filter(groups__name="marker").prefetch_related("auth_token")
    for x in markers:
        print(x)
    print("----")
    for x in lead_markers:
        print(x)
    print("----")
    for x in managers:
        print(x)
    print("----")
    for x in scanners:
        print(x)
    return []
