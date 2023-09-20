# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Brennen Chiu
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2022-2023 Colin B. Macdonald
# Copyright (C) 2022 Natalie Balashov

from django.contrib.auth.models import User, Group
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.forms import SetPasswordForm
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str
from django.views.generic import View
from braces.views import GroupRequiredMixin
from bs4 import BeautifulSoup
from random_username.generate import generate_username

from .services import generate_link, check_username, AuthenticationServices
from .signupForm import CreateManagerForm, CreateScannersAndMarkersForm
from Base.base_group_views import (
    AdminRequiredView,
    ManagerRequiredView,
    RoleRequiredView,
)


# Create your views here.
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

    def get(self, request, uidb64, token):
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
            context = {"form": reset_form, "help_text": self.help_text}
            return render(request, self.template_name, context)
        else:
            return render(request, self.reset_invalid)

    def post(self, request, uidb64, token):
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
                    error = parsed_error.li.text[13:]
                    context = {
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
                    error = parsed_error.li.text[13:]
                    context = {
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

    def get(self, request):
        return render(request, self.template_name, status=200)


# login_required make sure user is log in first
class Home(RoleRequiredView):
    login_url = "login/"
    redirect_field_name = "login"

    def get(self, request):
        context = {}
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
                return redirect("home")
            else:
                messages.info(request, "Username or Password is incorrect!")
            return render(request, self.template_name)


# Logout User
class LogoutView(View):
    def get(self, request):
        logout(request)
        return redirect("login")


# Signup Page
class Signup(ManagerRequiredView):
    template_name = "Authentication/signup.html"

    def get(self, request):
        context = {}
        return render(request, self.template_name, context)


# Signup Manager
class SignupManager(AdminRequiredView):
    template_name = "Authentication/manager_signup.html"
    activation_link = "Authentication/manager_activation_link.html"
    form = CreateManagerForm()

    def get(self, request):
        context = {"form": self.form}
        return render(request, self.template_name, context)

    def post(self, request):
        form = CreateManagerForm(request.POST)
        username = request.POST.get("username")
        exist_username = User.objects.filter(username__iexact=username)
        context = {}
        if form.is_valid() and not exist_username.exists():
            user = form.save()
            user.refresh_from_db()
            user.profile.email = form.cleaned_data.get("email")
            group = Group.objects.get(name="manager")
            user.groups.add(group)
            # user can't log in until the link is confirmed
            user.is_active = False
            user.save()
            link = generate_link(request, user)
            context.update(
                {
                    "user_email": user.profile.email,
                    "link": link,
                }
            )
            return render(request, self.activation_link, context)
        else:
            if exist_username.exists():
                context.update(
                    {
                        "form": self.form,
                        "error": "A user with that username already exists.",
                    }
                )
                return render(request, self.template_name, context)
            context.update({"form": self.form, "error": form.errors})
            return render(request, self.template_name, context)


# Create Scanner and Marker users
class SignupScanners(ManagerRequiredView):
    template_name = "Authentication/scanner_signup.html"
    form = CreateScannersAndMarkersForm()
    __group_name = Group.objects.get(name="scanner").name

    def get(self, request):
        context = {
            "form": self.form,
            "created": False,
        }
        return render(request, self.template_name, context)

    def post(self, request):
        form = CreateScannersAndMarkersForm(request.POST)

        if form.is_valid():
            num_users = form.cleaned_data.get("num_users")
            username_choices = form.cleaned_data.get("basic_or_funky_username")

            if username_choices == "basic":
                usernames_list = (
                    AuthenticationServices().generate_list_of_basic_usernames(
                        group_name=self.__group_name, num_users=num_users
                    )
                )
            elif username_choices == "funky":
                usernames_list = (
                    AuthenticationServices().generate_list_of_funky_usernames(
                        num_users=num_users
                    )
                )

            password_reset_links = (
                AuthenticationServices().generate_password_reset_links_dict(
                    request=request, username_list=usernames_list
                )
            )

            context = {
                "form": self.form,
                "links": scanner_dict,
                "created": True,
            }
            return render(request, self.template_name, context)


# Signup Markers
class SignupMarkers(ManagerRequiredView):
    template_name = "Authentication/marker_signup.html"
    form = CreateScannersAndMarkersForm()
    __group_name = Group.objects.get(name="marker").name

    def get(self, request):
        context = {
            "form": self.form,
            "created": False,
        }
        return render(request, self.template_name, context)

    def post(self, request):
        form = CreateScannersAndMarkersForm(request.POST)

        if form.is_valid():
            num_users = form.cleaned_data.get("num_users")
            username_choices = form.cleaned_data.get("basic_or_funky_username")

            if username_choices == "basic":
                usernames_list = (
                    AuthenticationServices().generate_list_of_basic_usernames(
                        group_name=self.__group_name, num_users=num_users
                    )
                )
            elif username_choices == "funky":
                usernames_list = (
                    AuthenticationServices().generate_list_of_funky_usernames(
                        num_users=num_users
                    )
                )

            password_reset_links = (
                AuthenticationServices().generate_password_reset_links_dict(
                    request=request, username_list=usernames_list
                )
            )

            context = {
                "form": self.form,
                "links": marker_dict,
                "created": True,
            }
            return render(request, self.template_name, context)


class PasswordResetLinks(AdminRequiredView):
    template_name = "Authentication/regenerative_links.html"
    activation_link = "Authentication/manager_activation_link.html"

    def get(self, request):
        users = User.objects.all().filter(groups__name="manager").values()
        context = {"users": users}
        return render(request, self.template_name, context)

    def post(self, request):
        username = request.POST.get("new_link")
        user = User.objects.get(username=username)
        link = generate_link(request, user)
        context = {"link": link}
        return render(request, self.activation_link, context)


class Maintenance(Home, View):
    def get(self, request):
        context = {}
        return render(request, "Authentication/maintenance.html", context)
