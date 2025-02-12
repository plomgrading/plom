# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Edith Coates
# Copyright (C) 2023 Julian Lapenna
# Copyright (C) 2023 Divy Patel
# Copyright (C) 2024-2025 Colin B. Macdonald
# Copyright (C) 2024 Aidan Murphy
# Copyright (C) 2024 Aden Chan
# Copyright (C) 2024 Andrew Rechnitzer

from __future__ import annotations

import difflib
import json
from copy import deepcopy
from io import TextIOWrapper, StringIO, BytesIO
from typing import Any

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib import messages
from django.views.generic.edit import UpdateView

# TODO: Issue #3808
# from django.core.exceptions import ValidationError
from rest_framework.exceptions import ValidationError

from plom.feedback_rules import feedback_rules as static_feedback_rules
from plom.misc_utils import pprint_score

from Base.base_group_views import ManagerRequiredView
from Base.models import SettingsModel
from Papers.services import SpecificationService
from Preparation.services import PapersPrinted
from .services import RubricService
from .forms import (
    RubricHalfMarkForm,
    RubricDiffForm,
    RubricFilterForm,
    RubricUploadForm,
    RubricDownloadForm,
    RubricItemForm,
)
from .models import RubricTable


class RubricAdminPageView(ManagerRequiredView):
    """Initializing rubrics, maybe other features in the future."""

    def get(self, request: HttpRequest) -> HttpResponse:
        context = self.build_context()

        if not PapersPrinted.have_papers_been_printed():
            return render(request, "Finish/finish_not_printed.html", context=context)

        template_name = "Rubrics/rubrics_admin.html"
        rubric_halfmark_form = RubricHalfMarkForm(request.GET)
        download_form = RubricDownloadForm(request.GET)
        upload_form = RubricUploadForm()
        rubrics = RubricService.get_all_rubrics()
        half_point_rubrics = rubrics.filter(value__exact=0.5).filter(text__exact=".")
        context.update(
            {
                "rubrics": rubrics,
                "half_point_rubrics": half_point_rubrics,
                "rubric_halfmark_form": rubric_halfmark_form,
                "rubric_download_form": download_form,
                "rubric_upload_form": upload_form,
            }
        )
        return render(request, template_name, context=context)


class RubricHalfMarksView(ManagerRequiredView):
    """Create demo rubrics."""

    def post(self, request: HttpRequest) -> HttpResponse:
        any_manager = User.objects.filter(groups__name="manager").first()
        if not RubricService().build_half_mark_delta_rubrics(any_manager.username):
            messages.error(
                request,
                "\N{VULGAR FRACTION ONE HALF} mark rubrics could not be created.",
            )
        return redirect("rubrics_admin")


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
        """Get the landing page for displaying and analyzing rubrics."""
        context = self.build_context()
        if not SpecificationService.is_there_a_spec():
            return render(request, "Finish/finish_no_spec.html", context=context)
        if not PapersPrinted.have_papers_been_printed():
            return render(request, "Finish/finish_not_printed.html", context=context)

        template_name = "Rubrics/rubrics_landing.html"
        rubric_filter_form = RubricFilterForm
        rubric_form = RubricItemForm
        question_max_marks_dict = SpecificationService.get_questions_max_marks()

        filter_form = rubric_filter_form(request.GET)
        rubrics = RubricService.get_all_rubrics()

        if filter_form.is_valid():
            question_filter = filter_form.cleaned_data["question_filter"]
            kind_filter = filter_form.cleaned_data["kind_filter"]
            system_filter = filter_form.cleaned_data["system_filter"]

            if question_filter:
                rubrics = rubrics.filter(question_index=question_filter, latest=True)

            if kind_filter:
                rubrics = rubrics.filter(kind=kind_filter, latest=True)

            if system_filter:
                if system_filter == "System":
                    rubrics = rubrics.filter(system_rubric=True, latest=True)
                elif system_filter == "User":
                    rubrics = rubrics.filter(system_rubric=False, latest=True)

        # if the form is invalid, we default to showing all rubrics (?)

        for index, r in enumerate(rubrics):
            r.value_str = f"{r.value:.3g}"
            r.out_of_str = f"{r.out_of:.3g}"

        rubrics_table = RubricTable(rubrics, order_by=request.GET.get("sort"))
        rubrics_table.paginate(page=int(request.GET.get("page", 1)), per_page=20)

        # TODO: consider getting rid of this dumps stuff...  maybe plain ol' list?
        context.update(
            {
                "rubrics_table": rubrics_table,
                "rubric_filter_form": filter_form,
                "edit_form": rubric_form,
                "question_max_marks_dict": json.dumps(question_max_marks_dict),
            }
        )

        return render(request, template_name, context=context)


class RubricItemView(UpdateView, ManagerRequiredView):
    """A page for displaying a single rubric and its annotations.

    UpdateView is used to automatically populate the form with rubric data.
    """

    def get(self, request: HttpRequest, *, rid: int) -> HttpResponse:
        """Get a rubric item."""
        template_name = "Rubrics/rubric_item.html"
        rs = RubricService()
        question_max_marks_dict = SpecificationService.get_questions_max_marks()

        context = self.build_context()

        rubric = rs.get_rubric_by_rid(rid)
        revisions = rs.get_past_revisions_by_rid(rid)
        marking_tasks = rs.get_marking_tasks_with_rubric_in_latest_annotation(rubric)
        rubric_form = RubricItemForm(instance=rubric)
        # TODO: does this enumerate serve any purpose?  workaround for...?
        for _, task in enumerate(marking_tasks):
            task.latest_annotation.score_str = pprint_score(
                task.latest_annotation.score
            )

        rubric_as_html = rs.get_rubric_as_html(rubric)
        # TODO: consider getting rid of this dumps stuff...  maybe plain ol' list?
        context.update(
            {
                "latest_rubric": rubric,
                "rid": rid,
                "revisions": revisions,
                "marking_tasks": marking_tasks,
                "latest_rubric_as_html": rubric_as_html,
                "diff_form": RubricDiffForm(rid=rid),
                "edit_form": rubric_form,
                "question_max_marks_dict": json.dumps(question_max_marks_dict),
            }
        )

        return render(request, template_name, context=context)

    @staticmethod
    def post(request: HttpRequest, *, rid: int) -> HttpResponse:
        """Posting to a rubric item receives data from a form an updates a rubric."""
        form = RubricItemForm(request.POST)

        if form.is_valid():
            rs = RubricService()
            rubric = rs.get_rubric_by_rid(rid)
            for key, value in form.cleaned_data.items():
                rubric.__setattr__(key, value)
            rubric.save()
        return redirect("rubric_item", rid=rid)


def compare_rubrics(request, rid):
    """View for displaying a diff between two rubrics."""
    if request.method == "POST" and request.htmx:
        form = RubricDiffForm(request.POST, rid=rid)
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
    # dict, so use a list, sorted:
    #   - first by whether admins can override the defaults
    #   - secondly alphabetically by code
    L = []
    for code in sorted(rules.keys()):
        data = rules[code]
        # keep the overridable rules on top
        if data["override_allowed"]:
            data = data.copy()
            data.update({"code": code})
            L.append(data)
    for code in sorted(rules.keys()):
        data = rules[code]
        if not data["override_allowed"]:
            data = data.copy()
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
            data_string = service.get_rubric_data("json", question_idx=question)
            buf = StringIO(data_string)
            response = HttpResponse(buf.getvalue(), content_type="text/json")
            response["Content-Disposition"] = "attachment; filename=rubrics.json"
        elif filetype == "toml":
            data_string = service.get_rubric_data("toml", question_idx=question)
            buf2 = BytesIO(data_string.encode("utf-8"))
            response = HttpResponse(buf2.getvalue(), content_type="application/toml")
            response["Content-Disposition"] = "attachment; filename=rubrics.toml"
        else:
            data_string = service.get_rubric_data("csv", question_idx=question)
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

        try:
            service.update_rubric_data(data_string, suffix)
        except ValueError as e:
            messages.error(request, f"Error: {e}")
        except ValidationError as e:
            # TODO: what is the "right way" to render one of these?
            (errmsg,) = e.args
            messages.error(request, f"Error: {errmsg}")
        else:
            messages.success(request, "Rubric file uploaded successfully.")
        return redirect("rubrics_admin")


class RubricCreateView(ManagerRequiredView):
    """Handles the creation of new rubrices."""

    def post(self, request: HttpRequest) -> HttpResponse:
        """Posting from a form to the rubric creator makes a new rubric."""
        form = RubricItemForm(request.POST)
        if not form.is_valid():
            messages.error(request, f"invalid form data: {form.errors}")
            return redirect("rubrics_landing")
        rs = RubricService()
        rubric_data = {
            "user": request.user.pk,
            "modified_by_user": request.user.pk,
            "text": form.cleaned_data["text"],
            "kind": form.cleaned_data["kind"],
            "value": form.cleaned_data["value"],
            "out_of": form.cleaned_data["out_of"],
            "meta": form.cleaned_data["meta"],
            "question_index": form.cleaned_data["question_index"],
            "pedagogy_tags": form.cleaned_data["pedagogy_tags"],
        }
        rs.create_rubric(rubric_data)
        messages.success(request, "Rubric created successfully.")
        return redirect("rubrics_landing")


class RubricEditView(ManagerRequiredView):
    """Handles the editing of existing rubrices."""

    def post(self, request: HttpRequest, *, rid: int) -> HttpResponse:
        """Posting from a form to to edit an existing rubric."""
        form = RubricItemForm(request.POST)
        if not form.is_valid():
            messages.error(request, f"invalid form data: {form.errors}")
            return redirect("rubric_item", rid)
        rs = RubricService()
        rubric = rs.get_rubric_by_rid(rid)
        rubric_data = {
            "username": request.user.username,
            "text": form.cleaned_data["text"],
            "kind": form.cleaned_data["kind"],
            "value": form.cleaned_data["value"],
            "out_of": form.cleaned_data["out_of"],
            "meta": form.cleaned_data["meta"],
            "question_index": form.cleaned_data["question_index"],
            "versions": form.cleaned_data["versions"],
            "parameters": form.cleaned_data["parameters"],
            "revision": rubric.revision,
            "tags": form.cleaned_data["tags"],
            "pedagogy_tags": form.cleaned_data["pedagogy_tags"],
        }
        rs.modify_rubric(
            rid,
            new_rubric_data=rubric_data,
            modifying_user=User.objects.get(username=request.user.username),
            tag_tasks=False,
        )
        messages.success(request, "Rubric edited successfully.")
        return redirect("rubric_item", rid)
