# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Edith Coates
# Copyright (C) 2023 Julian Lapenna
# Copyright (C) 2023 Divy Patel
# Copyright (C) 2024 Colin B. Macdonald
# Copyright (C) 2024 Aidan Murphy
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
from django.views.generic.edit import UpdateView

from plom.feedback_rules import feedback_rules as static_feedback_rules
from plom.misc_utils import pprint_score

from Base.base_group_views import ManagerRequiredView
from Base.models import SettingsModel
from Papers.services import SpecificationService
from .services import RubricService
from .forms import (
    RubricAdminForm,
    RubricDemoAdminForm,
    RubricDiffForm,
    RubricWipeForm,
    RubricFilterForm,
    RubricUploadForm,
    RubricDownloadForm,
    RubricItemForm,
)
from .models import RubricTable


class RubricAdminPageView(ManagerRequiredView):
    """Initializing rubrics, maybe other features in the future."""

    def get(self, request: HttpRequest) -> HttpResponse:
        template_name = "Rubrics/rubrics_admin.html"
        form = RubricAdminForm(request.GET)
        rubric_demo_form = RubricDemoAdminForm(request.GET)
        download_form = RubricDownloadForm(request.GET)
        upload_form = RubricUploadForm()
        context = self.build_context()
        rubrics = RubricService.get_all_rubrics()
        demo_rubrics = rubrics.filter(value__exact=0.5).filter(text__exact=".")
        context.update(
            {
                "rubrics": rubrics,
                "demo_rubrics": demo_rubrics,
                "rubric_admin_form": form,
                "rubric_demo_admin_form": rubric_demo_form,
                "rubric_download_form": download_form,
                "rubric_upload_form": upload_form,
            }
        )
        return render(request, template_name, context=context)

    def post(self, request: HttpRequest) -> HttpResponse:
        template_name = "Rubrics/rubrics_admin.html"
        form = RubricAdminForm(request.POST)
        rubric_demo_form = RubricDemoAdminForm(request.GET)
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
                "rubric_demo_admin_form": rubric_demo_form,
                "rubric_download_form": download_form,
                "rubric_upload_form": upload_form,
            }
        )
        return render(request, template_name, context=context)


class RubricDemoView(ManagerRequiredView):
    """Create demo rubrics."""

    def post(self, request: HttpRequest) -> HttpResponse:
        any_manager = User.objects.filter(groups__name="manager").first()
        if not RubricService().build_half_mark_delta_rubrics(any_manager.username):
            messages.error(
                request,
                "\N{Vulgar Fraction One Half} mark rubrics could not be created.",
            )
        return redirect("rubrics_admin")


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

    def get(self, request: HttpRequest) -> HttpResponse:
        """Get the page the landing page for displaying and analyzing rubrics."""
        template_name = "Rubrics/rubrics_landing.html"
        rubric_filter_form = RubricFilterForm
        rubric_create_form = RubricItemForm
        questions = SpecificationService.get_questions_max_marks()

        context = self.build_context()

        filter_form = rubric_filter_form(request.GET)
        rubrics = RubricService.get_all_rubrics()

        if filter_form.is_valid():
            question_filter = filter_form.cleaned_data["question_filter"]
            kind_filter = filter_form.cleaned_data["kind_filter"]
            system_filter = filter_form.cleaned_data["system_filter"]

            if question_filter:
                rubrics = rubrics.filter(question=question_filter, latest=True)

            if kind_filter:
                rubrics = rubrics.filter(kind=kind_filter, latest=True)

            if system_filter:
                if system_filter == "System":
                    rubrics = rubrics.filter(system_rubric=True, latest=True)
                elif system_filter == "User":
                    rubrics = rubrics.filter(system_rubric=False, latest=True)

        for index, r in enumerate(rubrics):
            r.value_str = f"{r.value:.3g}"
            r.out_of_str = f"{r.out_of:.3g}"

        rubrics_table = RubricTable(rubrics, order_by=request.GET.get("sort"))
        rubrics_table.paginate(page=int(request.GET.get("page", 1)), per_page=20)

        context.update(
            {
                "rubrics": rubrics_table,
                "rubric_filter_form": filter_form,
                "rubric_create_form": rubric_create_form,
                "questions": json.dumps(questions),
            }
        )

        return render(request, template_name, context=context)


class RubricItemView(UpdateView, ManagerRequiredView):
    """A page for displaying a single rubric and its annotations.

    UpdateView is used to automatically populate the form with rubric data.
    """

    def get(self, request: HttpRequest, *, rubric_key: int) -> HttpResponse:
        """Get a rubric item."""
        template_name = "Rubrics/rubric_item.html"
        rs = RubricService()
        questions = SpecificationService.get_questions_max_marks()

        context = self.build_context()

        rubric = rs.get_rubric_by_key(rubric_key)
        revisions = rs.get_past_revisions_by_key(rubric_key)
        marking_tasks = rs.get_marking_tasks_with_rubric_in_latest_annotation(rubric)
        form = RubricItemForm(instance=rubric)
        for _, task in enumerate(marking_tasks):
            task.latest_annotation.score_str = pprint_score(
                task.latest_annotation.score
            )

        rubric_as_html = rs.get_rubric_as_html(rubric)
        context.update(
            {
                "latest_rubric": rubric,
                "rubric_key": rubric_key,
                "revisions": revisions,
                "marking_tasks": marking_tasks,
                "latest_rubric_as_html": rubric_as_html,
                "diff_form": RubricDiffForm(key=rubric_key),
                "form": form,
                "questions": json.dumps(questions),
            }
        )

        return render(request, template_name, context=context)

    @staticmethod
    def post(request: HttpRequest, *, rubric_key: int) -> HttpResponse:
        """Posting to a rubric item receives data from a form an updates a rubric."""
        form = RubricItemForm(request.POST)

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
        form = RubricDiffForm(request.POST, key=rubric_key)
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
    """Handles the creation of new rubrices."""

    def post(self, request: HttpRequest) -> HttpResponse:
        """Posting from a form to the rubric creator makes a new rubric."""
        form = RubricItemForm(request.POST)
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
                "pedagogy_tags": form.cleaned_data["pedagogy_tags"],
            }
            rs.create_rubric(rubric_data)
        messages.success(request, "Rubric created successfully.")
        return redirect("rubrics_landing")


class RubricEditView(ManagerRequiredView):
    """Handles the editing of existing rubrices."""

    def post(self, request: HttpRequest, rubric_key) -> HttpResponse:
        """Posting from a form to to edit an existing rubric."""
        rubric_key = str(rubric_key).zfill(12)
        form = RubricItemForm(request.POST)
        if form.is_valid():
            rs = RubricService()
            rubric = rs.get_rubric_by_key(rubric_key)
            rubric_data = {
                "username": request.user.username,
                "text": form.cleaned_data["text"],
                "kind": form.cleaned_data["kind"],
                "value": form.cleaned_data["value"],
                "out_of": form.cleaned_data["out_of"],
                "meta": form.cleaned_data["meta"],
                "question": form.cleaned_data["question"],
                "revision": rubric.revision,
                "pedagogy_tags": form.cleaned_data["pedagogy_tags"],
            }
            rs.modify_rubric(
                key=rubric_key,
                new_rubric_data=rubric_data,
                modifying_user=User.objects.get(username=request.user.username),
            )
        messages.success(request, "Rubric created successfully.")
        return redirect("rubric_item", rubric_key)
