# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Brennen Chiu
# Copyright (C) 2024 Aden Chan
# Copyright (C) 2024-2025 Colin B. Macdonald
# Copyright (C) 2024 Aidan Murphy
# Copyright (C) 2025 Andrew Rechnitzer

import csv
from io import StringIO

from django.conf import settings
from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist
from django.db import IntegrityError
from django.shortcuts import render

from plom.misc_utils import humanize_seconds
from plom_server.Base.base_group_views import AdminOrManagerRequiredView
from .services import AuthenticationServices
from .forms.signupForm import CreateSingleUserForm, CreateMultiUsersForm


def _common_make_csv_tsv(userlist: list[dict[str, str]]) -> tuple[str, str]:
    fieldnames = ["Username", "Reset Link"]
    with StringIO() as iostream:
        writer = csv.writer(iostream, delimiter="\t")
        writer.writerow(fieldnames)
        writer.writerows([[u["username"], u["link"]] for u in userlist])
        tsv_string = iostream.getvalue()
    with StringIO() as iostream:
        writer = csv.writer(iostream, delimiter=",")
        writer.writerow(fieldnames)
        writer.writerows([[u["username"], u["link"]] for u in userlist])
        csv_string = iostream.getvalue()
    return (csv_string, tsv_string)


class SingleUserSignUp(AdminOrManagerRequiredView):
    template_name = "Authentication/signup_single_user.html"
    link_expiry_period = humanize_seconds(settings.PASSWORD_RESET_TIMEOUT)

    def get(self, request):
        form = CreateSingleUserForm()
        context = {
            "form": form,
            "current_page": "single",
            "link_expiry_period": self.link_expiry_period,
        }
        return render(request, self.template_name, context)

    def post(self, request):
        form = CreateSingleUserForm(request.POST)
        context = {
            "form": form,
            "current_page": "single",
            "link_expiry_period": self.link_expiry_period,
        }
        if form.is_valid():
            username = form.cleaned_data.get("username")
            user_email = form.cleaned_data.get("email")
            group_names = form.cleaned_data.get("user_types")
            assert isinstance(group_names, list)

            created_username = AuthenticationServices.create_user_and_add_to_groups(
                username, group_names, email=user_email
            )
            usernames_list = list(created_username.split(" "))
            _links = AuthenticationServices().generate_password_reset_links_dict(
                request=request, username_list=usernames_list
            )

            # TODO: maybe groups should come back from the create_user_and_add_to_groups...?
            from django.contrib.auth.models import User

            user = User.objects.get(username=created_username)
            Groups = ", ".join(user.groups.values_list("name", flat=True))
            userlist = [
                {
                    "username": created_username,
                    "groups": Groups,
                    "link": _links[created_username],
                }
            ]
            context.update({"links": userlist})
        else:
            context.update({"error": form.errors})
        return render(request, self.template_name, context)


class MultiUsersSignUp(AdminOrManagerRequiredView):
    template_name = "Authentication/signup_multiple_users.html"
    link_expiry_period = humanize_seconds(settings.PASSWORD_RESET_TIMEOUT)

    def get(self, request):
        form = CreateMultiUsersForm()
        context = {
            "form": form,
            "current_page": "multiple",
            "link_expiry_period": self.link_expiry_period,
        }
        return render(request, self.template_name, context)

    def post(self, request):
        form = CreateMultiUsersForm(request.POST)
        if not form.is_valid():
            # yellow screen of death on dev, not sure on production
            raise RuntimeError("Unexpectedly invalid form")

        context = {
            "form": form,
            "current_page": "multiple",
            "link_expiry_period": self.link_expiry_period,
        }
        num_users = form.cleaned_data.get("num_users")
        username_choices = form.cleaned_data.get("basic_or_funky_username")
        user_type = form.cleaned_data.get("user_types")

        if username_choices == "basic":
            usernames_list = AuthenticationServices.make_multiple_numbered_users(
                num_users, group_name=user_type
            )
        elif username_choices == "funky":
            usernames_list = AuthenticationServices.make_multiple_funky_named_users(
                num_users, group_name=user_type
            )
        else:
            raise RuntimeError("Tertium non datur: unexpected third choice!")

        _links = AuthenticationServices().generate_password_reset_links_dict(
            request=request, username_list=usernames_list
        )
        # TODO: these are missing groups
        userlist = [
            {"username": k, "groups": "meh", "link": v} for k, v in _links.items()
        ]

        csv_string, tsv_string = _common_make_csv_tsv(userlist)
        context.update(
            {
                "links": userlist,
                "tsv": tsv_string,
                "csv": csv_string,
            }
        )
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
    valid_user_groups = AuthenticationServices.plom_user_groups_list

    def get(self, request):
        context = {
            "current_page": "import",
            "link_expiry_period": self.link_expiry_period,
            "example_input_csv": self.example_csv,
            "valid_user_groups": self.valid_user_groups,
        }
        return render(request, self.template_name, context)

    def post(self, request):
        context = {
            "current_page": "import",
            "link_expiry_period": self.link_expiry_period,
            "example_input_csv": self.example_csv,
            "valid_user_groups": self.valid_user_groups,
        }

        if request.FILES[".csv"].size > settings.MAX_FILE_SIZE:
            messages.error(
                request,
                f"{request.FILES['.csv']} exceeds the "
                f"{settings.MAX_FILE_SIZE_DISPLAY} file size limit",
            )
            return render(request, self.template_name, context)
        csv_bytes = request.FILES[".csv"].file.getvalue()

        try:
            userlist = AuthenticationServices().create_users_from_csv(csv_bytes)
        except (IntegrityError, KeyError, ValueError) as e:
            messages.error(request, str(e))
            return render(request, self.template_name, context)
        except ObjectDoesNotExist as e:
            messages.error(
                request,
                f"Problem with one or more rows in {request.FILES['.csv'].name}:\n"
                f"{e}\n The valid usergroups are: {', '.join(self.valid_user_groups)}.",
            )
            return render(request, self.template_name, context)

        csv_string, tsv_string = _common_make_csv_tsv(userlist)
        context.update(
            {
                "links": userlist,
                "tsv": tsv_string,
                "csv": csv_string,
            }
        )

        return render(request, self.template_name, context)
