# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Brennen Chiu
# Copyright (C) 2024 Aden Chan
# Copyright (C) 2024 Colin B. Macdonald

from django.conf import settings
from django.shortcuts import render

from plom.misc_utils import humanize_seconds
from ..services import AuthenticationServices
from ..form.signupForm import CreateUserForm, CreateMultiUsersForm
from Base.base_group_views import AdminOrManagerRequiredView


class SingleUserSignUp(AdminOrManagerRequiredView):
    template_name = "Authentication/signup_single_user.html"

    link_expiry_period = humanize_seconds(settings.PASSWORD_RESET_TIMEOUT)
    form = CreateUserForm()

    def get(self, request):
        context = {
            "form": self.form,
            "current_page": "single",
            "link_expiry_period": self.link_expiry_period,
        }
        return render(request, self.template_name, context)

    def post(self, request):
        form = CreateUserForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data.get("username")
            user_email = form.cleaned_data.get("email")
            user_type = form.cleaned_data.get("user_types")

            created_username = AuthenticationServices.create_user_and_add_to_group(
                username, group_name=user_type, email=user_email
            )
            usernames_list = list(created_username.split(" "))
            password_reset_links = (
                AuthenticationServices().generate_password_reset_links_dict(
                    request=request, username_list=usernames_list
                )
            )
            context = {
                "form": self.form,
                "current_page": "single",
                "link_expiry_period": self.link_expiry_period,
                "links": password_reset_links,
                "created": True,
            }
        else:
            context = {
                "form": form,
                "current_page": "single",
                "link_expiry_period": self.link_expiry_period,
                "created": False,
                # TODO: this looks overly specific: perhaps it could fail in many ways
                "error": form.errors["username"][0],
            }
        return render(request, self.template_name, context)


class MultiUsersSignUp(AdminOrManagerRequiredView):
    template_name = "Authentication/signup_multiple_users.html"
    form = CreateMultiUsersForm()
    link_expiry_period = humanize_seconds(settings.PASSWORD_RESET_TIMEOUT)

    def get(self, request):
        context = {
            "form": self.form,
            "current_page": "multiple",
            "link_expiry_period": self.link_expiry_period,
        }
        return render(request, self.template_name, context)

    def post(self, request):
        form = CreateMultiUsersForm(request.POST)

        if form.is_valid():
            num_users = form.cleaned_data.get("num_users")
            username_choices = form.cleaned_data.get("basic_or_funky_username")
            user_type = form.cleaned_data.get("user_types")

            if username_choices == "basic":
                usernames_list = (
                    AuthenticationServices().generate_list_of_basic_usernames(
                        group_name=user_type, num_users=num_users
                    )
                )
            elif username_choices == "funky":
                usernames_list = (
                    AuthenticationServices().generate_list_of_funky_usernames(
                        group_name=user_type, num_users=num_users
                    )
                )
            else:
                raise RuntimeError("Tertium non datur: unexpected third choice!")

            password_reset_links = (
                AuthenticationServices().generate_password_reset_links_dict(
                    request=request, username_list=usernames_list
                )
            )

            # Using tsv format for easy pasting into spreadsheet software
            tsv = "Username\tReset Link\n".format()
            for username, link in password_reset_links.items():
                append = "{}{}{}{}".format(username, "\t", link, "\n")
                tsv = tsv + append

            context = {
                "form": self.form,
                "current_page": "multiple",
                "link_expiry_period": self.link_expiry_period,
                "links": password_reset_links,
                "tsv": tsv,
                "created": True,
            }
            return render(request, self.template_name, context)
