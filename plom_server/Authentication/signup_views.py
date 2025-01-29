# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Brennen Chiu
# Copyright (C) 2024 Aden Chan
# Copyright (C) 2024-2025 Colin B. Macdonald
# Copyright (C) 2024 Aidan Murphy
# Copyright (C) 2025 Andrew Rechnitzer

from io import StringIO
import csv

from django.conf import settings
from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist
from django.db import IntegrityError
from django.shortcuts import render

from plom.misc_utils import humanize_seconds
from Base.base_group_views import AdminOrManagerRequiredView
from .services import AuthenticationServices
from .form.signupForm import CreateSingleUserForm, CreateMultiUsersForm


class SingleUserSignUp(AdminOrManagerRequiredView):
    template_name = "Authentication/signup_single_user.html"
    form = CreateSingleUserForm()
    link_expiry_period = humanize_seconds(settings.PASSWORD_RESET_TIMEOUT)

    def get(self, request):
        context = {
            "form": self.form,
            "current_page": "single",
            "link_expiry_period": self.link_expiry_period,
        }
        return render(request, self.template_name, context)

    def post(self, request):
        form = CreateSingleUserForm(request.POST)
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
                "form": form,
                "current_page": "single",
                "link_expiry_period": self.link_expiry_period,
                "links": password_reset_links,
            }
        else:
            context = {
                "form": form,
                "current_page": "single",
                "link_expiry_period": self.link_expiry_period,
                "error": form.errors,
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

        if not form.is_valid():
            # yellow screen of death on dev, not sure on production
            raise RuntimeError("Unexpectedly invalid form")

        num_users = form.cleaned_data.get("num_users")
        username_choices = form.cleaned_data.get("basic_or_funky_username")
        user_type = form.cleaned_data.get("user_types")

        if username_choices == "basic":
            usernames_list = AuthenticationServices().generate_list_of_basic_usernames(
                group_name=user_type, num_users=num_users
            )
        elif username_choices == "funky":
            usernames_list = AuthenticationServices().generate_list_of_funky_usernames(
                group_name=user_type, num_users=num_users
            )
        else:
            raise RuntimeError("Tertium non datur: unexpected third choice!")

        password_reset_links = (
            AuthenticationServices().generate_password_reset_links_dict(
                request=request, username_list=usernames_list
            )
        )

        # tsv's and csv's
        with StringIO() as iostream:
            writer = csv.writer(iostream, delimiter="\t")
            writer.writerows(password_reset_links.items())
            tsv_string = iostream.getvalue()

        fields = ["Username", "Reset Link"]
        with StringIO() as iostream:
            writer = csv.writer(iostream, delimiter=",")
            writer.writerow(fields)
            writer.writerows(password_reset_links.items())
            csv_string = iostream.getvalue()

        context = {
            "form": self.form,
            "current_page": "multiple",
            "link_expiry_period": self.link_expiry_period,
            "links": password_reset_links,
            "tsv": tsv_string,
            "csv": csv_string,
        }
        return render(request, self.template_name, context)


class ImportUsers(AdminOrManagerRequiredView):
    """Make many users from a formatted .csv file."""

    template_name = "Authentication/signup_import_users.html"
    link_expiry_period = humanize_seconds(settings.PASSWORD_RESET_TIMEOUT)
    example_csv = (
        "username,usergroup\n"
        "ExampleName1,marker\n"
        "ExampleName2,lead_marker\n"
        "ExampleName14,scanner\n"
        "exampleName37,manager"
    )
    # TODO: this bunch of strings should exist somewhere else
    user_groups = ["marker", "lead_marker", "scanner", "manager"]

    def get(self, request):
        context = {
            "current_page": "import",
            "link_expiry_period": self.link_expiry_period,
            "example_input_csv": self.example_csv,
            "user_groups": self.user_groups,
        }
        return render(request, self.template_name, context)

    def post(self, request):
        context = {
            "current_page": "import",
            "link_expiry_period": self.link_expiry_period,
            "example_input_csv": self.example_csv,
            "user_groups": self.user_groups,
        }

        if request.FILES[".csv"].size > settings.MAX_FILE_SIZE:
            messages.error(
                request,
                f"{request.FILES['.csv']} exceeds the "
                f"{settings.MAX_FILE_SIZE_DISPLAY} file size limit",
            )
            return render(request, self.template_name, context)
        csv_bytes = request.FILES[".csv"].file.getvalue()

        user_list = {}
        try:
            AuS = AuthenticationServices()
            user_list = AuS.create_users_from_csv(csv_bytes)
        except (IntegrityError, KeyError, ValueError) as e:
            messages.error(request, str(e))
            return render(request, self.template_name, context)
        except ObjectDoesNotExist:
            messages.error(
                request,
                # TODO: find the offending row[s] and tell the user.
                f"One or more rows in {request.FILES['.csv'].name} "
                " references an invalid usergroup.\n"
                f"The valid usergroups are: {', '.join(self.user_groups)}.",
            )
            return render(request, self.template_name, context)

        users = {user["username"]: user["reset_link"] for user in user_list}
        with StringIO() as iostream:
            writer = csv.DictWriter(
                iostream,
                fieldnames=list(user_list[0].keys()),
                delimiter="\t",
            )
            writer.writeheader()
            writer.writerows(user_list)
            tsv_string = iostream.getvalue()
        with StringIO() as iostream:
            writer = csv.DictWriter(
                iostream,
                fieldnames=list(user_list[0].keys()),
            )
            writer.writeheader()
            writer.writerows(user_list)
            csv_string = iostream.getvalue()

        context.update(
            {
                "links": users,
                "tsv": tsv_string,
                "csv": csv_string,
            }
        )

        return render(request, self.template_name, context)
