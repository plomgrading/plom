# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Edith Coates

from rest_framework.permissions import BasePermission, SAFE_METHODS


class AllowAnyReadOnly(BasePermission):
    """Allow authenticated and unauthenticated users to access only safe methods.

    The default permission is IsAuthenticated, see https://gitlab.com/plom/plom/-/issues/2904.
    """

    def has_permission(self, request, view):
        return request.method in SAFE_METHODS
