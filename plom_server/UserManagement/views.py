# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Chris Jin
# Copyright (C) 2022 Brennen Chiu
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2023 Colin B. Macdonald

from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User, Group

from django_htmx.http import HttpResponseClientRefresh

from Base.base_group_views import ManagerRequiredView


class UserPage(ManagerRequiredView):
    user_page = "UserManagement/users.html"

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
        return render(request, self.user_page, context)

    def post(self, request, username):
        user_to_change = User.objects.get_by_natural_key(username)

        # toggle active status
        user_to_change.is_active = not user_to_change.is_active
        user_to_change.save()

        return HttpResponseClientRefresh()

    @login_required
    def enableScanners(self):
        users_in_group = Group.objects.get(name="scanner").user_set.all()
        for user in users_in_group:
            user.is_active = True
            user.save()
        return redirect("/users")

    @login_required
    def disableScanners(self):
        users_in_group = Group.objects.get(name="scanner").user_set.all()
        for user in users_in_group:
            user.is_active = False
            user.save()
        return redirect("/users")

    @login_required
    def enableMarkers(self):
        users_in_group = Group.objects.get(name="marker").user_set.all()
        for user in users_in_group:
            user.is_active = True
            user.save()
        return redirect("/users")

    @login_required
    def disableMarkers(self):
        users_in_group = Group.objects.get(name="marker").user_set.all()
        for user in users_in_group:
            user.is_active = False
            user.save()
        return redirect("/users")

    @login_required
    def toggleLeadMarker(self, username):
        lead_marker_group = Group.objects.get(name="lead_marker")
        user_to_change = User.objects.get_by_natural_key(username)
        if lead_marker_group in user_to_change.groups.all():
            user_to_change.groups.remove(lead_marker_group)
        else:
            user_to_change.groups.add(lead_marker_group)
        user_to_change.save()
        return redirect("/users")


class ProgressPage(ManagerRequiredView):
    progress_page = "UserManagement/progress.html"

    def get(self, request, username):
        context = {"username": username}
        return render(request, self.progress_page, context)

    def post(self, request, username):
        return render(request, self.progress_page, username)
