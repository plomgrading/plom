# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Edith Coates

from rest_framework.permissions import BasePermission, SAFE_METHODS


class AllowAnyReadOnly(BasePermission):
    """Allow authenticated and unauthenticated users to access only safe methods.

    The default permission is IsAuthenticated, see https://gitlab.com/plom/plom/-/issues/2904.
    """

    def has_permission(self, request, view):
        return request.method in SAFE_METHODS


class IsManager(BasePermission):
    """Allow read and write access only to the manager."""

    def has_permission(self, request, view):
        user_groups = request.user.groups.values_list("name", flat=True)
        return "manager" in user_groups


class IsManagerReadOnly(BasePermission):
    """Allow read access only to the manager."""

    def has_permission(self, request, view):
        user_groups = request.user.groups.values_list("name", flat=True)
        return "manager" in user_groups and request.method in SAFE_METHODS


class IsManagerOrAuthenticatedReadOnly(BasePermission):
    """Allow read and write access to the manager, and read access to authenticated users."""

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        user_groups = request.user.groups.values_list("name", flat=True)
        if "manager" in user_groups:
            return True
        return request.method in SAFE_METHODS
