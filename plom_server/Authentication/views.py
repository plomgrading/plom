# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Brennen Chiu
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2022-2024 Colin B. Macdonald
# Copyright (C) 2022 Natalie Balashov

from __future__ import annotations

from typing import Any

from django.contrib.auth.models import User
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.forms import SetPasswordForm
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.sites.shortcuts import get_current_site
from django.http import HttpRequest, HttpResponse
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str
from django.views.generic import View
from braces.views import GroupRequiredMixin
from bs4 import BeautifulSoup

from .services import AuthenticationServices
from Base.base_group_views import (
    AdminRequiredView,
    RoleRequiredView,
)


# Set User Password
class SetPassword(View):
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
        try:
            uid = force_str((urlsafe_base64_decode(uidb64)))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            user = None
        if user is not None and default_token_generator.check_token(user, token):
            reset_form = SetPasswordForm(user, request.POST)

            # scanner and marker group
            if (
                user.groups.filter(name="scanner").exists()
                or user.groups.filter(name="marker").exists()
            ):
                if reset_form.is_valid():
                    user = reset_form.save()
                    user.is_active = True
                    user.profile.signup_confirmation = True
                    user.save()
                    return render(request, self.set_password_complete)
                # display error message
                else:
                    tri_quote = '"""'
                    error_message = tri_quote + str(reset_form.errors) + tri_quote
                    parsed_error = BeautifulSoup(error_message, "html.parser")
                    # MyPy unhappy with this code, me too a bit, hardcoded 13?!
                    assert parsed_error is not None
                    assert parsed_error.li is not None
                    error = parsed_error.li.text[13:]
                    context = {
                        "username": user.username,
                        "form": reset_form,
                        "help_text": SetPassword.help_text,
                        "error": error,
                    }
                    return render(request, self.template_name, context)

            # manager group
            else:
                if reset_form.is_valid():
                    user = reset_form.save()
                    user.is_active = True
                    user.profile.signup_confirmation = True
                    user.save()
                    return render(request, self.set_password_complete)
                # display error message
                else:
                    tri_quote = '"""'
                    error_message = tri_quote + str(reset_form.errors) + tri_quote
                    parsed_error = BeautifulSoup(error_message, "html.parser")
                    # MyPy unhappy with this code, me too a bit, hardcoded 13?!
                    assert parsed_error is not None
                    assert parsed_error.li is not None
                    error = parsed_error.li.text[13:]
                    context = {
                        "username": user.username,
                        "form": reset_form,
                        "help_text": SetPassword.help_text,
                        "error": error,
                    }
                    return render(request, self.template_name, context)
        else:
            return render(request, self.reset_invalid, status=403)


# When user enters their password successfully
class SetPasswordComplete(LoginRequiredMixin, GroupRequiredMixin, View):
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


# Login the user
class LoginView(View):
    template_name = "Authentication/login.html"

    def get(self, request):
        if request.user.is_authenticated:
            return redirect("home")
        return render(request, self.template_name)

    def post(self, request):
        if request.user.is_authenticated:
            return redirect("home")
        else:
            username = request.POST.get("username")
            temp_username = User.objects.filter(username__iexact=username).values()
            if not temp_username.exists():
                messages.info(request, "User does not exist!")
                return render(request, self.template_name)
            password = request.POST.get("password")
            user = authenticate(
                request, username=temp_username[0]["username"], password=password
            )
            if user is not None:
                login(request, user)
                if "next" in request.POST:
                    return redirect(request.POST.get("next"))
                else:
                    return redirect("home")
            else:
                messages.info(request, "Username or Password is incorrect!")
            return render(request, self.template_name)


# Logout User
class LogoutView(View):
    def get(self, request: HttpRequest) -> HttpResponse:
        logout(request)
        return redirect("login")


class PasswordResetLinks(AdminRequiredView):
    template_name = "Authentication/regenerative_links.html"
    activation_link = "Authentication/manager_activation_link.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        users = User.objects.all().filter(groups__name="manager").values()
        context = {"users": users}
        return render(request, self.template_name, context)

    def post(self, request: HttpRequest) -> HttpResponse:
        username = request.POST.get("new_link")
        user = User.objects.get(username=username)
        request_domain = get_current_site(request).domain
        link = AuthenticationServices().generate_link(user, request)
        context = {"link": link}
        return render(request, self.activation_link, context)


class Maintenance(Home, View):
    def get(self, request: HttpRequest) -> HttpResponse:
        context: dict[str, Any] = {}
        return render(request, "Authentication/maintenance.html", context)
