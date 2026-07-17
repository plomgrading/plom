# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2022 Brennen Chiu
# Copyright (C) 2023-2024 Andrew Rechnitzer
# Copyright (C) 2023, 2025-2026 Colin B. Macdonald
# Copyright (C) 2026 Aidan Murphy

from typing import Any

from braces.views import LoginRequiredMixin, GroupRequiredMixin
from django.contrib.auth.views import redirect_to_login
from django.views.generic import View
from django_htmx.http import HttpResponseClientRedirect

from plom_server.Authentication.services import AuthService


class RoleRequiredView(LoginRequiredMixin, GroupRequiredMixin, View):
    """A base class view for any authorised user."""

    group_required: tuple[str, ...] = AuthService.plom_user_groups_list
    raise_exception = True
    redirect_unauthenticated_users = True

    def build_context(self) -> dict[str, Any]:
        return {}

    # TODO: this is doing weird things when we prefix the server
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
            return HttpResponseClientRedirect(self.get_login_url())
        else:
            # send a normal redirect
            return redirect_to_login(
                request.get_full_path(),
                self.get_login_url(),
                self.get_redirect_field_name(),
            )


class AdminRequiredView(RoleRequiredView):
    """A class view for admins."""

    group_required = ("admin",)


class AdminOrManagerRequiredView(RoleRequiredView):
    """A class view for admins and managers."""

    group_required = ("admin", "manager")


class ManagerRequiredView(RoleRequiredView):
    """A class view for managers."""

    group_required = ("manager",)


class ScannerRequiredView(RoleRequiredView):
    """A class view for scanners."""

    group_required = ("scanner",)


class LeadMarkerRequiredView(RoleRequiredView):
    """A base class view for lead markers."""

    group_required = ("lead_marker",)


class LeadMarkerOrManagerView(RoleRequiredView):
    """A base class view for lead markers and managers."""

    group_required = ("lead_marker", "manager")


class IdentifierOrManagerView(RoleRequiredView):
    """A base class view for identifiers and managers."""

    group_required = ("identifier", "manager")


class IdentifierOrLeadMarkerOrManagerView(RoleRequiredView):
    """A base class view for identifiers, lead markers, or managers."""

    group_required = ("identifier", "lead_marker", "manager")


class IdentifierOrMarkerOrManagerView(RoleRequiredView):
    """A base class view for identifiers, markers, or managers."""

    group_required = ("identifier", "marker", "manager")


class MarkerRequiredView(RoleRequiredView):
    """A class view for markers."""

    group_required = ("marker",)


class MarkerOrManagerView(RoleRequiredView):
    """A base class view for markers (and thus lead markers) and managers."""

    group_required = ("marker", "manager")


class ScannerLeadMarkerOrManagerView(RoleRequiredView):
    """A base class view for scanners, lead markers and managers."""

    group_required = ("scanner", "lead_marker", "manager")


class IdentifierScannerLeadMarkerOrManagerView(RoleRequiredView):
    """A base class view for identifiers, scanners, lead markers and managers."""

    group_required = ("identifier", "scanner", "lead_marker", "manager")
