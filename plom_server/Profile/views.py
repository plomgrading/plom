# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Brennen Chiu
# Copyright (C) 2023-2025 Colin B. Macdonald
# Copyright (C) 2024 Aden Chan

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render, redirect
from django.views.generic import View
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.sites.shortcuts import get_current_site
from .edit_profile_form import EditProfileForm
from plom_server.Authentication.services import AuthenticationServices


class ProfileView(LoginRequiredMixin, View):
    """Class-based view of Profile page."""

    login_url = "login"
    profile_page = "Profile/profile.html"
    form = EditProfileForm()

    def get(self, request: HttpRequest) -> HttpResponse:
        """Get the current user profile page.

        Args:
            request: an Http request.

        Returns:
            Profile HTML page.
        """
        form = EditProfileForm(instance=request.user)
        try:
            # TODO: first?  but more generally, why not support multiple groups?
            group = request.user.groups.all()[0].name
        except IndexError:
            group = None
        context = {
            "form": form,
            "user_group": group,
            "email": request.user.email,
        }
        return render(request, self.profile_page, context)

    def post(self, request: HttpRequest) -> HttpResponse:
        """Edit the current user profile page.

        Args:
            request: an Http request.

        Returns:
            Profile HTML page.
        """
        try:
            # TODO: first?  but more generally, why not support multiple groups?
            group = request.user.groups.all()[0].name
        except IndexError:
            group = None
        form = EditProfileForm(request.POST, instance=request.user)
        if not form.is_valid():
            messages.error(request, f"Unexpectedly invalid form: {form}")
            return redirect("home")
        form.save()
        context = {
            "form": form,
            "user_group": group,
            "email": request.user.email,
        }
        return render(request, self.profile_page, context)


def password_change_redirect(request):
    request_domain = get_current_site(request).domain
    link = AuthenticationServices().generate_link(request.user, request_domain)
    return redirect(link)
