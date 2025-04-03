# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Chris Jin
# Copyright (C) 2022 Brennen Chiu
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2023-2025 Colin B. Macdonald
# Copyright (C) 2023-2024 Andrew Rechnitzer
# Copyright (C) 2024 Elisa Pan
# Copyright (C) 2024 Bryan Tanady
# Copyright (C) 2025 Aidan Murphy

import json

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.sites.shortcuts import get_current_site
from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpRequest, HttpResponse, Http404
from django_htmx.http import HttpResponseClientRefresh
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect, render
from django.urls import reverse

from plom.misc_utils import humanize_seconds
from plom_server.Authentication.services import AuthenticationServices
from plom_server.Base.base_group_views import ManagerRequiredView
from plom_server.Progress.services.userinfo_service import UserInfoServices
from .services import PermissionChanger
from .services import QuotaService
from .services.UsersService import get_user_info, delete_user
from .models import Quota


class UserPage(ManagerRequiredView):
    """Class that handles the views in UserInfo Page.

    This page utilizes extra tags embedded in messages to display messages
    in different parts/cards in the page.

    modify_quota: is the tag used when one interacts with set and modify
        quota buttons.
    modify_default_limit: when one interacts with "Change Default Limit" button".
    set_quota_confirmation: the tag for the confirmation dialog interaction.
    """

    def get(self, request: HttpRequest) -> HttpResponse:
        """Fetch user management page."""
        users = get_user_info()
        # fetch these so that we don't loop over this in the template
        # remove db hits in loops.
        uids = cache.get("online-now", [])

        online_keys = ["online-%s" % (u,) for u in uids]
        fresh = cache.get_many(online_keys).keys()
        online_now_ids = [int(k.replace("online-", "")) for k in fresh]

        context = {
            "online_now_ids": online_now_ids,
            "scanners": users["scanners"],
            "markers": users["markers"],
            "lead_markers": users["lead_markers"],
            "managers": users["managers"],
            "users_with_quota_by_pk": QuotaService.get_list_of_user_pks_with_quotas(),
        }
        return render(request, "UserManagement/users.html", context)

    def post(self, request: HttpRequest, username: str) -> HttpResponse:
        """Set user to active or inactive."""
        PermissionChanger.toggle_user_active(username)

        return HttpResponseClientRefresh()

    def delete(self, request: HttpRequest, username: str) -> HttpResponse:
        """Delete user."""
        try:
            delete_user(username, request.user.id)
        except (ValueError, ObjectDoesNotExist) as e:
            messages.error(request, e, extra_tags="danger")
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
        return HttpResponseClientRefresh()


class PasswordResetPage(ManagerRequiredView):
    """View for displaying the password reset page."""

    def get(self, request: HttpRequest, *, username: str) -> HttpResponse:
        """Get the password reset page for a particular user."""
        user_obj = User.objects.get(username=username)
        request_domain = get_current_site(request).domain
        link = AuthenticationServices().generate_link(user_obj, request_domain)
        context = {
            "username": username,
            "link": link,
            "link_expiry_period": humanize_seconds(settings.PASSWORD_RESET_TIMEOUT),
        }
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


class SetQuotaView(ManagerRequiredView):
    """View to handle setting a quota limit for a user.

    Note: force_set_quota is a special flag that causes a marker's quota to be set
    even though they do not fulfill the limit restriction.  The limit will be set
    to their current number of question marked.
    """

    def post(self, request: HttpRequest, *, username: str) -> HttpResponse:
        """Handle the POST request to set the quota limit for the specified user."""
        user = get_object_or_404(User, username=username)
        next_page = request.POST.get(
            "next", request.META.get("HTTP_REFERER", reverse("users"))
        )

        # Special flag received when user confirms to force setting, ignoring limit restriction.
        if "force_set_quota" in request.POST:
            complete, claimed = (
                UserInfoServices.get_total_annotated_and_claimed_count_by_user(username)
            )
            quota, created = Quota.objects.get_or_create(user=user, limit=complete)

        # No special flag received, proceed to check whether the marker fulfills the restriction.
        elif QuotaService.can_set_quota(user):
            quota, created = Quota.objects.get_or_create(
                user=user, limit=Quota.default_limit
            )
            if not created:
                quota.limit = Quota.default_limit
                quota.save()

        # Message is specially crafted for confirmation dialog.
        else:
            details = {
                "username": username,
            }
            messages.info(
                request, json.dumps(details), extra_tags="set_quota_confirmation"
            )

        return redirect(next_page)


class UnsetQuotaView(ManagerRequiredView):
    """View to handle removing a quota limit from a user."""

    def post(self, request: HttpRequest, *, username: str) -> HttpResponse:
        """Handle the POST request to unset the quota limit for the specified user."""
        user = get_object_or_404(User, username=username)
        quota = Quota.objects.filter(user=user)
        quota.delete()

        next_page = request.POST.get(
            "next", request.META.get("HTTP_REFERER", reverse("users"))
        )
        return redirect(next_page)


class EditQuotaLimitView(ManagerRequiredView):
    """View to handle editing the quota limit for a user."""

    def post(self, request: HttpRequest) -> HttpResponse:
        """Handle the POST request to update the quota limit for the specified user."""
        username = request.POST.get("username")
        new_limit = int(request.POST.get("limit"))
        user = get_object_or_404(User, username=username)

        if QuotaService.can_set_quota(user, limit=new_limit):
            quota = Quota.objects.filter(user=user).first()
            quota.limit = new_limit
            quota.save()
            messages.success(
                request,
                "Quota limit updated successfully.",
                extra_tags="modify_quota",
            )
        else:
            messages.error(request, "Invalid Limit!", extra_tags="modify_quota")

        previous_url = request.META.get("HTTP_REFERER", reverse("users"))
        return redirect(previous_url)


class ModifyQuotaView(ManagerRequiredView):
    """View to handle modifying the quota state and/or limit for multiple users."""

    def post(self, request: HttpRequest) -> HttpResponse:
        """Handle the POST request to update the quota limits for the specified users."""
        user_ids = request.POST.getlist("users")
        new_limit = int(request.POST.get("limit"))
        valid_markers, invalid_markers = QuotaService.set_quotas_for_userlist(
            user_ids, new_limit
        )

        if len(invalid_markers) > 0:
            messages.success(
                request,
                f"Quota limit has been successfully updated for: {', '.join(valid_markers)}",
                extra_tags="modify_quota",
            )
            messages.error(
                request,
                f"Invalid limit for: {', '.join(invalid_markers)}",
                extra_tags="modify_quota",
            )
        else:
            messages.success(
                request,
                "All quota limits updated successfully.",
                extra_tags="modify_quota",
            )
        return redirect(reverse("progress_user_info_home"))


class ModifyDefaultLimitView(ManagerRequiredView):
    """View to handle modifying the default quota limit."""

    def post(self, request: HttpRequest) -> HttpResponse:
        """Handle the POST request to change the default limit."""
        new_limit = int(request.POST.get("limit"))

        if new_limit > 0:
            Quota.set_default_limit(new_limit)
            messages.success(
                request,
                "Default limit updated successfully.",
                extra_tags="modify_default_limit",
            )
        else:
            messages.error(
                request, "Limit is invalid!", extra_tags="modify_default_limit"
            )

        previous_url = request.META.get("HTTP_REFERER", reverse("users"))
        return redirect(previous_url)


class BulkSetQuotaView(ManagerRequiredView):
    """View to handle bulk setting quota for all markers."""

    def post(self, request: HttpRequest) -> HttpResponse:
        """Post to set the quota for all markers."""
        markers = User.objects.filter(groups__name="marker")
        markers_with_warnings = []
        successful_markers = []

        for marker in markers:
            if QuotaService.can_set_quota(marker):
                quota, created = Quota.objects.get_or_create(
                    user=marker,
                    defaults={"limit": Quota.default_limit},
                )
                successful_markers.append(marker.username)
            else:
                markers_with_warnings.append(marker.username)

        if markers_with_warnings:
            messages.success(
                request,
                f"A quota limit has been successfully set for: {', '.join(successful_markers)}",
                extra_tags="modify_quota",
            )

            messages.error(
                request,
                f"Quota cannot be set on: {', '.join(markers_with_warnings)}",
                extra_tags="modify_quota",
            )

            messages.warning(
                request, f"{markers_with_warnings}", extra_tags="quota_warning"
            )

        else:
            messages.success(
                request,
                "All markers have had a quota applied.",
                extra_tags="modify_quota",
            )

        return redirect(reverse("progress_user_info_home"))


class BulkUnsetQuotaView(ManagerRequiredView):
    """View to handle bulk unsetting of quota for all markers."""

    def post(self, request: HttpRequest) -> HttpResponse:
        """Post to unset the quota for all markers."""
        markers = User.objects.filter(groups__name="marker")
        Quota.objects.filter(user__in=markers).delete()
        messages.success(request, "Quota removed from all markers.")
        return redirect(reverse("progress_user_info_home"))
