# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Brennen Chiu
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2022-2024 Colin B. Macdonald
# Copyright (C) 2022 Natalie Balashov
# Copyright (C) 2024 Aidan Murphy

from __future__ import annotations

from typing import Any

from django.contrib.auth.models import User
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.forms import SetPasswordForm
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpRequest, HttpResponse
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str
from django.views.generic import View
from braces.views import GroupRequiredMixin

from Base.base_group_views import RoleRequiredView


class SetPassword(View):
    """Setting or resetting user passwords."""

    template_name = "Authentication/set_password.html"
    reset_invalid = "Authentication/activation_invalid.html"
    set_password_complete = "Authentication/set_password_complete.html"
    group_required = ["manager", "scanner", "marker"]
    help_text = [
        "Your password can’t be too similar to your other personal information.",
        "Your password must contain at least 8 characters.",
        "Your password can’t be a commonly used password.",
        "Your password can’t be entirely numeric.",
    ]

    def get(self, request: HttpRequest, uidb64: str, token: str) -> HttpResponse:
        """Get the password setting page."""
        try:
            uid = force_str((urlsafe_base64_decode(uidb64)))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            user = None
        reset_form = SetPasswordForm(user)
        if user is not None and default_token_generator.check_token(user, token):
            user.is_active = True
            user.profile.signup_confirmation = False
            user.save()
            context = {
                "form": reset_form,
                "help_text": self.help_text,
                "username": user.username,
            }
            return render(request, self.template_name, context)
        else:
            return render(request, self.reset_invalid)

    def post(self, request: HttpRequest, uidb64: str, token: str) -> HttpResponse:
        """Attempt to set a user's password."""
        try:
            uid = force_str((urlsafe_base64_decode(uidb64)))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            user = None

        if user is None or not default_token_generator.check_token(user, token):
            return render(request, self.reset_invalid, status=403)

        reset_form = SetPasswordForm(user, request.POST)

        if reset_form.is_valid():
            user = reset_form.save()
            user.is_active = True
            user.profile.signup_confirmation = True
            user.save()
            return render(request, self.set_password_complete)
        else:
            error_dict = dict(reset_form.errors)
            context = {
                "username": user.username,
                "form": reset_form,
                "help_text": SetPassword.help_text,
                "error_dict": error_dict,
            }
            return render(request, self.template_name, context)


class SetPasswordComplete(LoginRequiredMixin, GroupRequiredMixin, View):
    """Displayed when user has successfully completed setting their password."""

    template_name = "Authentication/set_password_complete.html"
    login_url = "login"
    group_required = ["manager", "marker", "scanner"]
    raise_exception = True

    def get(self, request: HttpRequest) -> HttpResponse:
        return render(request, self.template_name, status=200)


# login_required make sure user is log in first
class Home(RoleRequiredView):
    login_url = "login/"
    redirect_field_name = "login"

    def get(self, request: HttpRequest) -> HttpResponse:
        context: dict[str, Any] = {}
        return render(request, "Authentication/home.html", context)


class LoginView(View):
    """The login page and action of logging in."""

    template_name = "Authentication/login.html"

    def get(self, request):
        """Get the login page."""
        if request.user.is_authenticated:
            return redirect("home")
        return render(request, self.template_name)

    def post(self, request):
        """Attempt to authenticate and log in."""
        if request.user.is_authenticated:
            return redirect("home")

        username = request.POST.get("username")
        """be wary making db calls for unauthenticated users, see #3733
        temp_username = User.objects.filter(username__iexact=username).values()
        if not temp_username.exists():
            messages.info(request, "User does not exist!")
            return render(request, self.template_name)
        """
        user = authenticate(
            request,
            username=username,
            password=request.POST.get("password"),
        )
        if user is None:
            messages.info(request, "Username or Password is incorrect!")
            return render(request, self.template_name)

        login(request, user)
        if "next" in request.POST:
            return redirect(request.POST.get("next"))
        else:
            return redirect("home")


class LogoutView(View):
    """Logout a user."""

    def get(self, request: HttpRequest) -> HttpResponse:
        logout(request)
        return redirect("login")


class Maintenance(Home, View):
    """The accounts maintenance page."""

    def get(self, request: HttpRequest) -> HttpResponse:
        context: dict[str, Any] = {}
        return render(request, "Authentication/maintenance.html", context)
