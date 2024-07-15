# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Edith Coates
# Copyright (C) 2023 Julian Lapenna
# Copyright (C) 2023 Divy Patel
# Copyright (C) 2024 Colin B. Macdonald
# Copyright (C) 2024 Aden Chan

from __future__ import annotations

from copy import deepcopy
import difflib
import json
from typing import Any
from io import TextIOWrapper, StringIO, BytesIO

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.http import HttpResponseRedirect
from django.shortcuts import render, redirect, reverse
from django.contrib.auth.models import User
from django.contrib import messages

from plom.feedback_rules import feedback_rules as static_feedback_rules

from Base.base_group_views import ManagerRequiredView
from Base.models import SettingsModel
from Papers.services import SpecificationService
from .services import RubricService
from .forms import (
    RubricAdminForm,
    RubricWipeForm,
    RubricUploadForm,
    RubricFilterForm,
    RubricEditForm,
    RubricDownloadForm,
    RubricCreateForm,
)
from .models import RubricTable


class RubricAdminPageView(ManagerRequiredView):
    """Initializing rubrics, maybe other features in the future."""

    def get(self, request: HttpRequest) -> HttpResponse:
        template_name = "Rubrics/rubrics_admin.html"
        form = RubricAdminForm(request.GET)
        download_form = RubricDownloadForm(request.GET)
        upload_form = RubricUploadForm()
        context = self.build_context()
        rubrics = RubricService.get_all_rubrics()
        context.update(
            {
                "rubrics": rubrics,
                "rubric_admin_form": form,
                "rubric_download_form": download_form,
                "rubric_upload_form": upload_form,
            }
        )
        return render(request, template_name, context=context)

    def post(self, request: HttpRequest) -> HttpResponse:
        template_name = "Rubrics/rubrics_admin.html"
        form = RubricAdminForm(request.POST)
        download_form = RubricDownloadForm(request.GET)
        upload_form = RubricUploadForm()
        context = self.build_context()
        if form.is_valid():
            # TODO: not necessarily the one who logged in; does it matter?
            any_manager = User.objects.filter(groups__name="manager").first()
            RubricService().init_rubrics(any_manager.username)
        # and if not valid, this just kinda DTRT (?)
        rubrics = RubricService.get_all_rubrics()
        context.update(
            {
                "rubrics": rubrics,
                "rubric_admin_form": form,
                "rubric_download_form": download_form,
                "rubric_upload_form": upload_form,
            }
        )
        return render(request, template_name, context=context)


class RubricWipePageView(ManagerRequiredView):
    """Confirm before wiping rubrics."""

    def get(self, request: HttpRequest) -> HttpResponse:
        template_name = "Rubrics/rubrics_wipe.html"
        context = self.build_context()
        form = RubricWipeForm()
        # TODO: what is supposed to happen if we don't have a shortname yet?
        # TODO: do we need a `get_shortname_or_None`?  Related to Issue #2996
        context.update(
            {
                "rubric_wipe_form": form,
                "short_name": SpecificationService.get_shortname(),
                "long_name": SpecificationService.get_longname(),
                "n_rubrics": RubricService().get_rubric_count(),
            }
        )
        return render(request, template_name, context=context)

    def post(self, request: HttpRequest) -> HttpResponse:
        template_name = "Rubrics/rubrics_wipe.html"
        context = self.build_context()
        form = RubricWipeForm(request.POST)
        short_name = SpecificationService.get_shortname()
        _confirm_field = "confirm_by_typing_the_short_name"
        if form.is_valid():
            if form.cleaned_data[_confirm_field] == short_name:
                RubricService().erase_all_rubrics()
                return HttpResponseRedirect(reverse("rubrics_landing"))
            form.add_error(_confirm_field, "Short name did not match")
        context.update(
            {
                "rubric_wipe_form": form,
                "short_name": SpecificationService.get_shortname(),
                "long_name": SpecificationService.get_longname(),
                "n_rubrics": RubricService().get_rubric_count(),
            }
        )
        return render(request, template_name, context=context)


class RubricAccessPageView(ManagerRequiredView):
    """Highlevel control of who can modify/create rubrics."""

    def get(self, request: HttpRequest) -> HttpResponse:
        template_name = "Rubrics/rubrics_access.html"

        settings = SettingsModel.load()

        if settings.who_can_create_rubrics == "permissive":
            create_checked = (True, False, False)
        elif settings.who_can_create_rubrics == "locked":
            create_checked = (False, False, True)
        else:
            create_checked = (False, True, False)

        if settings.who_can_modify_rubrics == "permissive":
            modify_checked = (True, False, False)
        elif settings.who_can_modify_rubrics == "locked":
            modify_checked = (False, False, True)
        else:
            modify_checked = (False, True, False)

        context = self.build_context()
        context.update(
            {
                "successful_post": False,
                "create0_checked": create_checked[0],
                "create1_checked": create_checked[1],
                "create2_checked": create_checked[2],
                "modify0_checked": modify_checked[0],
                "modify1_checked": modify_checked[1],
                "modify2_checked": modify_checked[2],
            }
        )
        return render(request, template_name, context=context)

    def post(self, request: HttpRequest) -> HttpResponse:
        template_name = "Rubrics/rubrics_access.html"
        create = request.POST.get("create", None)
        modify = request.POST.get("modify", None)

        settings = SettingsModel.load()

        if create not in ("permissive", "per-user", "locked"):
            # TODO: 406?
            raise ValueError(f"create={create} is invalid")
        settings.who_can_create_rubrics = create
        settings.save()

        if modify not in ("permissive", "per-user", "locked"):
            # TODO: 406?
            raise ValueError(f"modify={modify} is invalid")
        settings.who_can_modify_rubrics = modify
        settings.save()

        if settings.who_can_create_rubrics == "permissive":
            create_checked = (True, False, False)
        elif settings.who_can_create_rubrics == "locked":
            create_checked = (False, False, True)
        else:
            create_checked = (False, True, False)

        if settings.who_can_modify_rubrics == "permissive":
            modify_checked = (True, False, False)
        elif settings.who_can_modify_rubrics == "locked":
            modify_checked = (False, False, True)
        else:
            modify_checked = (False, True, False)

        context = self.build_context()
        context.update(
            {
                "successful_post": True,
                "create0_checked": create_checked[0],
                "create1_checked": create_checked[1],
                "create2_checked": create_checked[2],
                "modify0_checked": modify_checked[0],
                "modify1_checked": modify_checked[1],
                "modify2_checked": modify_checked[2],
            }
        )
        return render(request, template_name, context=context)


class RubricLandingPageView(ManagerRequiredView):
    """A landing page for displaying and analyzing rubrics."""

    def get(self, request):
        template_name = "Rubrics/rubrics_landing.html"
        rubric_filter_form = RubricFilterForm
        rubric_create_form = RubricCreateForm

        context = self.build_context()

        filter_form = rubric_filter_form(request.GET)
        rubrics = RubricService.get_all_rubrics()

        if filter_form.is_valid():
            question_filter = filter_form.cleaned_data["question_filter"]
            kind_filter = filter_form.cleaned_data["kind_filter"]

            if question_filter:
                rubrics = rubrics.filter(question=question_filter, latest=True)

            if kind_filter:
                rubrics = rubrics.filter(kind=kind_filter, latest=True)

        rubrics = RubricTable(rubrics, order_by=request.GET.get("sort"))
        rubrics.paginate(page=request.GET.get("page", 1), per_page=15)
        context.update(
            {
                "rubrics": rubrics,
                "rubric_filter_form": filter_form,
                "rubric_create_form": rubric_create_form,
            }
        )

        return render(request, template_name, context=context)


class RubricItemView(ManagerRequiredView):
    """A page for displaying a single rubric and its annotations."""

    def get(self, request, rubric_key):
        template_name = "Rubrics/rubric_item.html"
        rs = RubricService()
        form = RubricEditForm

        context = self.build_context()

        # we need to pad the number with zeros on the left since if the keystarts
        # with a zero, it will be interpreted as a 11 digit key, which result in an error
        rubric_key = str(rubric_key).zfill(12)
        rubric = rs.get_rubric_by_key(rubric_key)
        revisions = rs.get_past_revisions_by_key(rubric_key)
        marking_tasks = rs.get_marking_tasks_with_rubric_in_latest_annotation(rubric)

        rubric_as_html = rs.get_rubric_as_html(rubric)
        context.update(
            {
                "latest_rubric": rubric,
                "revisions": revisions,
                "form": form(instance=rubric),
                "marking_tasks": marking_tasks,
                "latest_rubric_as_html": rubric_as_html,
                "diff_form": RubricDiffForm(key=rubric_key),
            }
        )

        return render(request, template_name, context=context)

    @staticmethod
    def post(request, rubric_key):
        form = RubricEditForm(request.POST)

        # we need to pad the number with zeros on the left since if the keystarts
        # with a zero, it will be interpreted as a 11 digit key, which result in an error
        rubric_key = str(rubric_key).zfill(12)

        if form.is_valid():
            rs = RubricService()
            rubric = rs.get_rubric_by_key(rubric_key)
            for key, value in form.cleaned_data.items():
                rubric.__setattr__(key, value)
            rubric.save()
        return redirect("rubric_item", rubric_key=rubric_key)


def compare_rubrics(request, rubric_key):
    """View for displaying a diff between two rubrics."""
    if request.method == "POST" and request.htmx:
        form = RubricDiffForm(request.POST, key=str(rubric_key).zfill(12))
        if form.is_valid():
            left = [
                f'{form.cleaned_data["left_compare"].display_delta} | {form.cleaned_data["left_compare"].text}'
            ]
            right = [
                f'{form.cleaned_data["right_compare"].display_delta} | {form.cleaned_data["right_compare"].text}'
            ]
            html = difflib.HtmlDiff(wrapcolumn=20).make_table(
                left,
                right,
                f'Rev. {form.cleaned_data["left_compare"].revision}',
                f'Rev. {form.cleaned_data["right_compare"].revision}',
            )
            return render(request, "Rubrics/diff_partial.html", {"diff": html})
        return JsonResponse({"errors": form.errors}, status=400)


def _rules_as_list(rules: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    # something (possible jsonfield) is randomly re-ordering the Python
    # dict, so use a list, sorted alphabetically by code (TODO: for now!)
    L = []
    for code in sorted(rules.keys()):
        data = rules[code].copy()
        data.update({"code": code})
        L.append(data)
    return L


class FeedbackRulesView(ManagerRequiredView):
    """Viewing and changing the defaults around potentially problem cases in annotation."""

    def get(self, request: HttpRequest) -> HttpResponse:
        template_name = "Rubrics/feedback_rules.html"
        context = self.build_context()
        settings = SettingsModel.load()
        rules = settings.feedback_rules
        if not rules:
            rules = static_feedback_rules
        context.update(
            {
                "feedback_rules": _rules_as_list(rules),
            }
        )
        return render(request, template_name, context=context)

    def post(self, request: HttpRequest) -> HttpResponse:
        template_name = "Rubrics/feedback_rules.html"
        settings = SettingsModel.load()
        # decide if we are resetting or updating the rules from the form
        if request.POST.get("_whut_do") == "reset":
            rules = {}
        else:
            rules = settings.feedback_rules
            if not rules:
                # carefully make a copy so we don't mess with the static data
                rules = deepcopy(static_feedback_rules)
            for code in rules.keys():
                x = request.POST.get(f"{code}-allowed", None)
                rules[code]["allowed"] = True if x is not None else False
                x = request.POST.get(f"{code}-warn", None)
                rules[code]["warn"] = True if x is not None else False
                x = request.POST.get(f"{code}-dama_allowed", None)
                rules[code]["dama_allowed"] = True if x is not None else False
        settings.feedback_rules = rules
        settings.save()

        # essentially a copy-paste of get from here :(
        context = self.build_context()
        settings = SettingsModel.load()
        rules = settings.feedback_rules
        if not rules:
            rules = static_feedback_rules
        context.update(
            {
                "successful_post": True,
                "feedback_rules": _rules_as_list(rules),
            }
        )
        return render(request, template_name, context=context)


class DownloadRubricView(ManagerRequiredView):
    def get(self, request: HttpRequest):
        service = RubricService()
        question = request.GET.get("question_filter")
        filetype = request.GET.get("file_type")

        if question is not None and len(question) != 0:
            question = int(question)
        else:
            question = None

        if filetype == "json":
            data_string = service.get_rubric_data("json", question=question)
            buf = StringIO(data_string)
            response = HttpResponse(buf.getvalue(), content_type="text/json")
            response["Content-Disposition"] = "attachment; filename=rubrics.json"
        elif filetype == "toml":
            data_string = service.get_rubric_data("toml", question=question)
            buf2 = BytesIO(data_string.encode("utf-8"))
            response = HttpResponse(buf2.getvalue(), content_type="application/toml")
            response["Content-Disposition"] = "attachment; filename=rubrics.toml"
        else:
            data_string = service.get_rubric_data("csv", question=question)
            buf3 = StringIO(data_string)
            response = HttpResponse(buf3.getvalue(), content_type="text/csv")
            response["Content-Disposition"] = "attachment; filename=rubrics.csv"
        return response


class UploadRubricView(ManagerRequiredView):
    def post(self, request: HttpRequest):
        service = RubricService()
        suffix = request.FILES["rubric_file"].name.split(".")[-1]

        if suffix == "csv" or suffix == "json":
            f = TextIOWrapper(request.FILES["rubric_file"], encoding="utf-8")
            data_string = f.read()
        elif suffix == "toml":
            f2 = BytesIO(request.FILES["rubric_file"].file.read())
            data_string = f2.getvalue().decode("utf-8")
        else:
            messages.error(request, "Invalid rubric file format")
            return redirect("rubrics_admin")

        service.update_rubric_data(data_string, suffix)
        messages.success(request, "Rubric file uploaded successfully.")
        return redirect("rubrics_admin")


class RubricCreateView(ManagerRequiredView):
    def post(self, request: HttpRequest):
        form = RubricCreateForm(request.POST)
        if form.is_valid():
            rs = RubricService()
            rubric_data = {
                "user": request.user.pk,
                "modified_by_user": request.user.pk,
                "text": form.cleaned_data["text"],
                "kind": form.cleaned_data["kind"],
                "value": form.cleaned_data["value"],
                "out_of": form.cleaned_data["out_of"],
                "meta": form.cleaned_data["meta"],
                "question": form.cleaned_data["question"],
            }
            print(rubric_data)
            rs.create_rubric(rubric_data)
        messages.success(request, "Rubric created successfully.")
        return redirect("rubrics_landing")
