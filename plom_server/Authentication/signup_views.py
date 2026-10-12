# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Brennen Chiu
# Copyright (C) 2024 Aden Chan
# Copyright (C) 2024-2025 Colin B. Macdonald
# Copyright (C) 2024, 2026 Aidan Murphy
# Copyright (C) 2025 Andrew Rechnitzer

import csv
from io import StringIO

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.db import IntegrityError
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache

from plom.common.misc_utils import humanize_seconds
from plom_server.Base.base_group_views import AdminOrManagerRequiredView
from .services import AuthService
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


class UserSignUp(AdminOrManagerRequiredView):
    """A page to signup new users."""

    def get(self, request):
        """Render the page."""
        example_input_csv = (
            "username,usergroups\n"
            "ExampleName1,marker\n"
            "ExampleName2,lead_marker\n"
            "ExampleName14,scanner\n"
            'ExampleName18,"marker,scanner"\n'
            "exampleName37,manager"
        )
        context = {
            "multiple_user_form": CreateMultiUsersForm(),
            "single_user_form": CreateSingleUserForm(),
            "example_input_csv": example_input_csv,
            "valid_user_groups": AuthService.plom_user_groups_list,
            "link_expiry_period": humanize_seconds(settings.PASSWORD_RESET_TIMEOUT),
        }
        return render(request, "Authentication/signup_users.html", context)


# we apply the decorator to the dispatch method, so it applies to all functions
# in this class view.
# https://docs.djangoproject.com/en/6.1/topics/class-based-views/intro/#decorating-the-class
@method_decorator(never_cache, name="dispatch")
class SingleUserCreation(AdminOrManagerRequiredView):
    """A view for handling single user creation.

    This is separate from the rendering view because
    we need to instruct the browser not to cache the response.
    """

    def post(self, request):
        form = CreateSingleUserForm(request.POST)
        context = {
            "form": form,
            "current_page": "single",
            "link_expiry_period": humanize_seconds(settings.PASSWORD_RESET_TIMEOUT),
        }
        if not form.is_valid():
            return render(
                request,
                "Authentication/password_reset_link_err.html",
                {"error_html": str(form.errors)},
                status=409,
            )

        username = form.cleaned_data.get("username")
        user_email = form.cleaned_data.get("email")
        group_names = form.cleaned_data.get("user_types")
        assert isinstance(group_names, list)

        created_username, groups_list = AuthService.create_user_and_add_to_groups(
            username, group_names, email=user_email
        )
        _links = AuthService().generate_password_reset_links_dict(
            request=request, username_list=[created_username]
        )
        userlist = [
            {
                "username": created_username,
                "groups": ", ".join(groups_list),
                "link": _links[created_username],
            }
        ]
        context.update({"links": userlist})
        return render(
            request, "Authentication/password_reset_link_modal_fragment.html", context
        )


@method_decorator(never_cache, name="dispatch")
class MultiUsersCreation(AdminOrManagerRequiredView):
    """Create multiple users simultaneously.

    This is separate from the rendering view because
    we need to instruct the browser not to cache the response.
    """

    def post(self, request):
        form = CreateMultiUsersForm(request.POST)
        if not form.is_valid():
            return render(
                request,
                "Authentication/password_reset_link_err.html",
                {"error_html": str(form.errors)},
                status=409,
            )

        context = {
            "form": form,
            "current_page": "multiple",
            "link_expiry_period": humanize_seconds(settings.PASSWORD_RESET_TIMEOUT),
        }
        num_users = form.cleaned_data.get("num_users")
        username_choices = form.cleaned_data.get("basic_or_funky_username")
        user_type = form.cleaned_data.get("user_types")

        if username_choices == "basic":
            users_and_groups = AuthService.make_multiple_numbered_users(
                num_users, group_name=user_type
            )
        elif username_choices == "funky":
            users_and_groups = AuthService.make_multiple_funky_named_users(
                num_users, group_name=user_type
            )
        else:
            return render(
                request,
                "Authentication/password_reset_link_err.html",
                {"error_html": "Tertium non datur: unexpected third choice!"},
                status=400,
            )

        _links_dict = AuthService().generate_password_reset_links_dict(
            request=request, username_list=[x[0] for x in users_and_groups]
        )
        # for u, g in users_and_groups:
        userlist = [
            {"username": u, "groups": ", ".join(g), "link": _links_dict[u]}
            for u, g in users_and_groups
        ]

        csv_string, tsv_string = _common_make_csv_tsv(userlist)
        context.update(
            {
                "links": userlist,
                "tsv": tsv_string,
                "csv": csv_string,
            }
        )
        return render(
            request, "Authentication/password_reset_link_modal_fragment.html", context
        )


@method_decorator(never_cache, name="dispatch")
class ImportUsersCreation(AdminOrManagerRequiredView):
    """Create users via import.

    This is separate from the rendering view because
    we need to instruct the browser not to cache the response.
    """

    def post(self, request):
        if request.FILES[".csv"].size > settings.MAX_FILE_SIZE:
            msg = f"""
                {request.FILES['.csv']} exceeds the
                {settings.MAX_FILE_SIZE_DISPLAY} file size limit
            """
            return render(
                request,
                "Authentication/password_reset_link_err.html",
                {"error_html": msg},
                status=400,
            )
        csv_bytes = request.FILES[".csv"].file.getvalue()

        try:
            userlist = AuthService.create_users_from_csv(csv_bytes)
        except (IntegrityError, KeyError, ValueError) as e:
            return render(
                request,
                "Authentication/password_reset_link_err.html",
                {"error_html": e},
                status=400,
            )
        except ObjectDoesNotExist as e:
            msg = f"""
                Problem with one or more rows in {request.FILES['.csv'].name}:\n
                {e}\n The valid usergroups are: {', '.join(AuthService.plom_user_groups_list)}.
            """
            return render(
                request,
                "Authentication/password_reset_link_err.html",
                {"error_html": msg},
                status=400,
            )

        for u in userlist:
            u["groups"] = ", ".join(u["groups"])
        csv_string, tsv_string = _common_make_csv_tsv(userlist)
        context = {
            "links": userlist,
            "tsv": tsv_string,
            "csv": csv_string,
        }

        return render(
            request, "Authentication/password_reset_link_modal_fragment.html", context
        )
