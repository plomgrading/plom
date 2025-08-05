# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2022 Brennen Chiu
# Copyright (C) 2023-2024 Andrew Rechnitzer
# Copyright (C) 2023, 2025 Colin B. Macdonald

from typing import Any

from django.views.generic import View
from braces.views import LoginRequiredMixin, GroupRequiredMixin
from django.urls import reverse

from django.contrib.auth.views import redirect_to_login
from django_htmx.http import HttpResponseClientRedirect


class RoleRequiredView(LoginRequiredMixin, GroupRequiredMixin, View):
    """A base class view for any authorised user."""

    group_required = ["admin", "manager", "scanner", "marker", "lead_marker"]
    login_url = "login"
    raise_exception = True
    redirect_unauthenticated_users = True

    def build_context(self) -> dict[str, Any]:
        return {}

    # this is adapted from the django braces source code for access-required-mixin
    def no_permissions_fail(self, request=None):
        """Called when the user has no permissions and no exception was raised.

        This should only return a valid HTTP response.
        Redirects to login using normal django calls unless HTMX headers present
        and then redirect via an htmx redirect call.
        """
        # check if request is from htmx by checking the meta info
        # https://stackoverflow.com/questions/70510216/how-can-i-check-if-the-current-request-is-from-htmx
        if request.META.get("HTTP_HX_REQUEST"):
            # is htmx so send a htmx redirect to the login url
            return HttpResponseClientRedirect(reverse(self.login_url))
        else:
            # send a normal redirect
            return redirect_to_login(
                request.get_full_path(),
                self.get_login_url(),
                self.get_redirect_field_name(),
            )


class AdminRequiredView(RoleRequiredView):
    """A class view for admins."""

    group_required = ["admin"]


class AdminOrManagerRequiredView(RoleRequiredView):
    """A class view for admins and managers."""

    group_required = ["admin", "manager"]


class ManagerRequiredView(RoleRequiredView):
    """A class view for managers."""

    group_required = ["manager"]


class ScannerRequiredView(RoleRequiredView):
    """A class view for scanners."""

    group_required = ["scanner"]


class LeadMarkerRequiredView(RoleRequiredView):
    """A base class view for lead markers."""

    group_required = ["lead_marker"]


class LeadMarkerOrManagerView(RoleRequiredView):
    """A base class view for lead markers and managers."""

    group_required = ["lead_marker", "manager"]


class MarkerRequiredView(RoleRequiredView):
    """A class view for markers."""

    group_required = ["marker"]


class MarkerLeadMarkerOrManagerView(RoleRequiredView):
    """A base class view for markers, lead markers and managers."""

    group_required = ["marker", "lead_marker", "manager"]


class ScannerLeadMarkerOrManagerView(RoleRequiredView):
    """A base class view for scanners, lead markers and managers."""

    group_required = ["scanner", "lead_marker", "manager"]
