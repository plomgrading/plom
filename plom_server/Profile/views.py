# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Brennen Chiu
# Copyright (C) 2023 Colin B. Macdonald

from django.shortcuts import render
from django.views.generic import View
from django.contrib.auth.mixins import LoginRequiredMixin
from .edit_profile_form import EditProfileForm


class Profile(LoginRequiredMixin, View):
    """Class-based view of Profile page."""

    login_url = "login"
    profile_page = "Profile/profile.html"
    navbar_colour = {
        "admin": "#808080",
        "manager": "#AD9CFF",
        "marker": "#FF434B",
        "scanner": "#0F984F",
    }
    form = EditProfileForm()

    def get(self, request):
        """Get the current user profile page.

        Args:
            request

        Returns:
            Profile HTML page.
        """
        form = EditProfileForm(instance=request.user)
        try:
            user = request.user.groups.all()[0].name
        except IndexError:
            user = None
        if user in Profile.navbar_colour:
            colour = Profile.navbar_colour[user]
        else:
            colour = "#000000"
            context = {
                "form": form,
                "navbar_colour": colour,
                "user_group": user,
                "email": request.user.email,
            }
            return render(request, self.profile_page, context)
        context = {
            "form": form,
            "navbar_colour": colour,
            "user_group": user,
            "email": request.user.email,
        }
        return render(request, self.profile_page, context, status=200)

    def post(self, request):
        """Edit the current user profile page.

        Args:
            request

        Returns:
            Profile HTML page.
        """
        try:
            user = request.user.groups.all()[0].name
        except IndexError:
            user = None
        if user in Profile.navbar_colour:
            colour = Profile.navbar_colour[user]
        form = EditProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            context = {
                "form": form,
                "navbar_colour": colour,
                "user_group": user,
                "email": request.user.email,
            }
            return render(request, self.profile_page, context, status=200)
