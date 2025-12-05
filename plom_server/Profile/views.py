# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Brennen Chiu
# Copyright (C) 2023-2025 Colin B. Macdonald
# Copyright (C) 2024 Aden Chan
# Copyright (C) 2025 Bryan Tanady
# Copyright (C) 2025 Aidan Murphy

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.sites.shortcuts import get_current_site
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render, redirect
from django.views.generic import View

from plom_server.Authentication.services import AuthenticationServices
from plom_server.Base.base_group_views import ManagerRequiredView
from plom_server.UserManagement.services import UsersService
from .edit_profile_form import EditProfileForm


class PrivateProfileView(LoginRequiredMixin, View):
    """Class-based private view of Profile page.

    So named 'Private' because each user can only view their own.
    """

    def get(self, request: HttpRequest) -> HttpResponse:
        """Get the current user profile page.

        Args:
            request: an Http request.

        Returns:
            Profile HTML page.
        """
        form = EditProfileForm(instance=request.user)
        try:
            # concatenate group names separated with a comma and a space
            groups = ", ".join([g.name for g in request.user.groups.all()])
        except IndexError:
            groups = ""
        context = {
            "form": form,
            "user_groups": groups,
        }
        return render(request, "Profile/private_profile.html", context)

    def post(self, request: HttpRequest) -> HttpResponse:
        """Edit the current user profile page.

        Args:
            request: an Http request.

        Returns:
            Profile HTML page.
        """
        form = EditProfileForm(request.POST, instance=request.user)
        if not form.is_valid():
            # raise ValidationError("Invalid form: " + form.errors.as_text())
            # TODO: what should the error handling be?
            messages.error(request, f"Unexpectedly invalid form: {form}")
            return redirect("home")
        form.save()
        return redirect("private_profile")


def password_change_redirect(request):
    request_domain = get_current_site(request).domain
    link = AuthenticationServices().generate_link(request.user, request_domain)
    return redirect(link)


class ProfileView(ManagerRequiredView):
    """Actions related to public facing user profiles."""

    def get(self, request: HttpRequest, *, username: str) -> HttpResponse:
        """Get the profile page as seen by another user.

        Args:
            request: an Http request.

        Keyword Args:
            username: the username of the user's profile to fetch.

        Returns:
            An HTML page.
        """
        user_dict = UsersService.get_user_as_dict(username)
        user_groups = UsersService.get_users_groups_info()[username]
        context = {
            "user": user_dict,
            "user_groups": ", ".join(user_groups),
        }
        return render(request, "Profile/profile.html", context)
