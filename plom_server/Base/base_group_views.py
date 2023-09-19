# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2022 Brennen Chiu
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2023 Colin B. Macdonald

from django.views.generic import View
from braces.views import LoginRequiredMixin, GroupRequiredMixin


class RoleRequiredView(LoginRequiredMixin, GroupRequiredMixin, View):
    """A base class view for admins."""

    group_required = ["admin", "manager", "scanner", "marker", "lead_marker"]
    login_url = "login"
    raise_exception = True
    redirect_unauthenticated_users = True

    def build_context(self):
        return {}


class AdminRequiredView(RoleRequiredView):
    """A base class view for any authorised user."""

    group_required = ["admin"]


class ManagerRequiredView(RoleRequiredView):
    """A base class view for managers."""

    group_required = ["manager"]


class ScannerRequiredView(RoleRequiredView):
    """A base class view for scanners."""

    group_required = ["scanner"]


class MarkerRequiredView(RoleRequiredView):
    """A base class view for markers."""

    group_required = ["marker"]


class LeadMarkerRequiredView(RoleRequiredView):
    """A base class view for markers."""

    group_required = ["lead_marker"]
