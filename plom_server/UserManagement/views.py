# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Chris Jin
# Copyright (C) 2022 Brennen Chiu
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2023-2024 Colin B. Macdonald
# Copyright (C) 2023-2024 Andrew Rechnitzer

from django.shortcuts import redirect, render
from django.http import HttpRequest, HttpResponse, Http404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User

from django_htmx.http import HttpResponseClientRefresh

from Base.base_group_views import ManagerRequiredView

from .services import PermissionChanger

from Authentication.services import AuthenticationServices

from django.shortcuts import get_object_or_404
from django.urls import reverse
from .models import ProbationPeriod


class UserPage(ManagerRequiredView):
    def get(self, request):
        managers = User.objects.filter(groups__name="manager")
        scanners = User.objects.filter(groups__name="scanner")
        lead_markers = User.objects.filter(groups__name="lead_marker")
        markers = User.objects.filter(groups__name="marker").prefetch_related(
            "auth_token"
        )
        probation_users = ProbationPeriod.objects.values_list("user_id", flat=True)
        context = {
            "scanners": scanners,
            "markers": markers,
            "lead_markers": lead_markers,
            "managers": managers,
            "probation_users": probation_users,
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


class HTMXExplodeView(ManagerRequiredView):
    """For debugging, this view causes some sorts of errors non-deterministically."""

    def get(self, request: HttpRequest) -> HttpResponse:
        """For debugging, Getting this randomly fails with 404 or a server 500 error or succeeds."""
        import random

        if random.random() < 0.333:
            1 / 0
        if random.random() < 0.5:
            raise Http404("Should happen 1/3 of the time")
        return HttpResponse("Button pushed", status=200)


class SetProbationView(ManagerRequiredView):
    def post(self, request, username):
        user = get_object_or_404(User, username=username)
        probation_period, created = ProbationPeriod.objects.get_or_create(
            user=user, defaults={"limit": 20}
        )
        if not created:
            probation_period.limit = 20
            probation_period.save()
        return redirect(reverse("users"))


class UnsetProbationView(ManagerRequiredView):
    def post(self, request, username):
        user = get_object_or_404(User, username=username)
        probation_period = ProbationPeriod.objects.filter(user=user)
        probation_period.delete()
        return redirect(reverse("users"))
