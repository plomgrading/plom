# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Chris Jin
# Copyright (C) 2022 Brennen Chiu
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2023-2024 Colin B. Macdonald
# Copyright (C) 2023 Andrew Rechnitzer

from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User

from django_htmx.http import HttpResponseClientRefresh

from Base.base_group_views import ManagerRequiredView

from .services import PermissionChanger

from Authentication.services import AuthenticationServices


class UserPage(ManagerRequiredView):
    def get(self, request):
        managers = User.objects.filter(groups__name="manager")
        scanners = User.objects.filter(groups__name="scanner")
        lead_markers = User.objects.filter(groups__name="lead_marker")
        markers = User.objects.filter(groups__name="marker").prefetch_related(
            "auth_token"
        )
        context = {
            "scanners": scanners,
            "markers": markers,
            "lead_markers": lead_markers,
            "managers": managers,
        }
        return render(request, "UserManagement/users.html", context)

    def post(self, request, username):
        PermissionChanger.toggle_user_active(username)

        return HttpResponseClientRefresh()

    @login_required
    def enableScanners(self):
        PermissionChanger.set_all_scanners_active(True)
        return redirect("/users")

    @login_required
    def disableScanners(self):
        PermissionChanger.set_all_scanners_active(False)
        return redirect("/users")

    @login_required
    def enableMarkers(self):
        PermissionChanger.set_all_markers_active(True)
        return redirect("/users")

    @login_required
    def disableMarkers(self):
        PermissionChanger.set_all_markers_active(False)
        return redirect("/users")

    @login_required
    def toggleLeadMarker(self, username):
        PermissionChanger.toggle_lead_marker_group_membership(username)
        return redirect("/users")


class PasswordResetPage(ManagerRequiredView):
    def get(self, request, username):
        user_obj = User.objects.get(username=username)
        link = AuthenticationServices().generate_link(request, user_obj)

        context = {"username": username, "link": link}
        return render(request, "UserManagement/password_reset_page.html", context)
