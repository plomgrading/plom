# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Edith Coates
# Copyright (C) 2023 Julian Lapenna
# Copyright (C) 2023 Divy Patel
# Copyright (C) 2024-2026 Colin B. Macdonald
# Copyright (C) 2024 Aidan Murphy
# Copyright (C) 2024 Aden Chan
# Copyright (C) 2024 Andrew Rechnitzer
# Copyright (C) 2025 Bryan Tanady
# Copyright (C) 2025 Deep Shah

import difflib
import json
from io import TextIOWrapper, StringIO, BytesIO
from typing import Any

from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib import messages
from django.views.generic.edit import UpdateView
from rest_framework import serializers

from plom.plom_exceptions import PlomConflict

from plom.misc_utils import pprint_score

from plom_server.Base.base_group_views import ManagerRequiredView
from plom_server.Base.services import Settings
from plom_server.Papers.services import SpecificationService
from plom_server.Preparation.services import PapersPrinted
from .services import RubricService, RubricPermissionsService
from .forms import (
    RubricCreateHalfMarkForm,
    RubricDiffForm,
    RubricFilterForm,
    RubricUploadForm,
    RubricDownloadForm,
    RubricItemForm,
    RubricTemplateDownloadForm,
)
from .models import RubricTable


class RubricAdminPageView(ManagerRequiredView):
    """Initializing rubrics, maybe other features in the future."""

    def get(self, request: HttpRequest) -> HttpResponse:
        context = self.build_context()

        if not PapersPrinted.have_papers_been_printed():
            return render(request, "Finish/finish_not_printed.html", context=context)

        template_name = "Rubrics/rubrics_admin.html"
        rubric_create_halfmark_form = RubricCreateHalfMarkForm(request.GET)
        download_form = RubricDownloadForm(request.GET)
        upload_form = RubricUploadForm()
        template_form = RubricTemplateDownloadForm()
        rubrics = RubricService.get_all_rubrics()
        # TODO: flaky?
        half_point_rubrics = rubrics.filter(value__exact=0.5).filter(text__exact=".")
        rubric_fractional_options = RubricPermissionsService.get_fractional_settings()
        context.update(
            {
                "rubrics": rubrics,
                "half_point_rubrics": half_point_rubrics,
                "rubric_fractional_options": rubric_fractional_options,
                "rubric_create_halfmark_form": rubric_create_halfmark_form,
                "rubric_download_form": download_form,
                "rubric_upload_form": upload_form,
                "rubric_template_form": template_form,
            }
        )
        return render(request, template_name, context=context)


class RubricCreateHalfMarksView(ManagerRequiredView):
    """Create half-point rubrics."""

    def post(self, request: HttpRequest) -> HttpResponse:
        any_manager = User.objects.filter(groups__name="manager").first()
        try:
            RubricService.build_half_mark_delta_rubrics(any_manager.username)
        except ValueError as e:
            messages.error(request, e)
        return redirect("rubrics_admin")


class RubricFractionalPreferencesView(ManagerRequiredView):
    """Set fractional rubric preferences."""

    def post(self, request: HttpRequest) -> HttpResponse:
        RubricPermissionsService.change_fractional_settings(request.POST)
        return redirect("rubrics_admin")


class RubricAccessPageView(ManagerRequiredView):
    """Highlevel control of who can modify/create rubrics."""

    def get(self, request: HttpRequest) -> HttpResponse:
        """Render the form for who can modify/create rubrics."""
        template_name = "Rubrics/rubrics_access.html"

        create = Settings.get_who_can_create_rubrics()
        modify = Settings.get_who_can_modify_rubrics()

        if create == "permissive":
            create_checked = (True, False, False)
        elif create == "locked":
            create_checked = (False, False, True)
        else:
            create_checked = (False, True, False)

        if modify == "permissive":
            modify_checked = (True, False, False)
        elif modify == "locked":
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
        """Accept changes to who can modify/create rubrics."""
        template_name = "Rubrics/rubrics_access.html"
        create = request.POST.get("create", None)
        modify = request.POST.get("modify", None)

        # These can throw ValueError: do we want a 406?
        Settings.set_who_can_create_rubrics(create)
        Settings.set_who_can_modify_rubrics(modify)

        if create == "permissive":
            create_checked = (True, False, False)
        elif create == "locked":
            create_checked = (False, False, True)
        else:
            create_checked = (False, True, False)

        if modify == "permissive":
            modify_checked = (True, False, False)
        elif modify == "locked":
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
        question_max_marks_dict = SpecificationService.get_questions_max_marks()

        context = self.build_context()

        rubric = RubricService.get_rubric_by_rid(rid)
        revisions = RubricService.get_past_revisions_by_rid(rid)
        marking_tasks = (
            RubricService.get_marking_tasks_with_rubric_in_latest_annotation(rubric)
        )
        rubric_form = RubricItemForm(instance=rubric)
        for task in marking_tasks:
            task.latest_annotation.score_str = pprint_score(
                task.latest_annotation.score
            )

        rubric_as_html = RubricService.get_rubric_as_html(rubric)
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


class RubricCompareView(ManagerRequiredView):
    """View for comparing Rubrics.

    Called by HTMX.
    """

    def post(self, request: HttpRequest, *, rid: int) -> HttpResponse:
        """View for displaying a diff between revisions of a Rubric.

        Args:
            request: an HTML POST request, which includes more
                details about which revisions to compare.
            rid: which overall Rubric are we looking at?

        Returns:
            On success, you get a fragment of HTML comparing
            two rubrics.
            If there are errors, such as asking about non-existent
            Rubrics, you get a 400 response with error information
            in JSON.
            Its an error to call this NOT from HTMX: you get a 418
            ("I'm a teapot") b/c its a bit odd in this author's
            opinion to dictate how folks call your code, so a joke
            response is as good as anything else.
        """
        if not request.htmx:
            return HttpResponse(
                "Only HTMX requests should post here; no coffee addicts allowed",
                status=418,
            )
        form = RubricDiffForm(request.POST, rid=rid)
        if not form.is_valid():
            return JsonResponse({"errors": form.errors}, status=400)
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
        rules = Settings.get_feedback_rules()
        context.update(
            {
                "feedback_rules": _rules_as_list(rules),
            }
        )
        return render(request, template_name, context=context)

    def post(self, request: HttpRequest) -> HttpResponse:
        template_name = "Rubrics/feedback_rules.html"
        # decide if we are resetting or updating the rules from the form
        if request.POST.get("_whut_do") == "reset":
            rules = {}
        else:
            rules = Settings.get_feedback_rules()
            for code in rules.keys():
                x = request.POST.get(f"{code}-allowed", None)
                rules[code]["allowed"] = True if x is not None else False
                x = request.POST.get(f"{code}-warn", None)
                rules[code]["warn"] = True if x is not None else False
                x = request.POST.get(f"{code}-dama_allowed", None)
                rules[code]["dama_allowed"] = True if x is not None else False
        Settings.key_value_store_set("feedback_rules", rules)

        # essentially a copy-paste of get from here :(
        context = self.build_context()
        Settings.get_feedback_rules()
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
    """Handles uploading of rubrics from data containing in a file."""

    def post(self, request: HttpRequest):
        """Posting a file of rubric data creates new rubrics."""
        suffix = request.FILES["rubric_file"].name.split(".")[-1]
        username = request.user.username

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
            RubricService.create_rubrics_from_file_data(
                data_string, suffix, by_system=False, requesting_user=username
            )
        except ValueError as e:
            messages.error(request, f"Error: {e}")
        except serializers.ValidationError as e:
            # Not sure the "right way" to render a ValidationError:
            # If we use {e} like for ValueError above, it renders like this:
            #    Error: [ErrorDetails(string='invalid row in "parameters"...', code='invalid')]
            # which is messy for end-users.  This args hack makes it render like:
            #    Error: invalid row in "parameters"...
            # See also API/views/utils.py which does a similar hack.
            (nicer_err_msgs,) = e.args
            messages.error(request, f"Error: {nicer_err_msgs}")
        else:
            messages.success(request, "Rubric file uploaded successfully.")
        return redirect("rubrics_admin")


class DownloadRubricTemplateView(ManagerRequiredView):
    def get(self, request: HttpRequest):
        service = RubricService()
        question = request.GET.get("question_filter")
        filetype = request.GET.get("file_type")

        if question is not None and len(question) != 0:
            question = int(question)
        else:
            question = None

        if filetype == "json":
            data_string = service.create_rubric_template(
                question_index=question, filetype="json"
            )
            buf = StringIO(data_string)
            response = HttpResponse(buf.getvalue(), content_type="text/json")
            response["Content-Disposition"] = "attachment; filename=rubrics.json"
        elif filetype == "toml":
            data_string = service.create_rubric_template(
                question_index=question, filetype="toml"
            )
            buf2 = BytesIO(data_string.encode("utf-8"))
            response = HttpResponse(buf2.getvalue(), content_type="application/toml")
            response["Content-Disposition"] = "attachment; filename=rubrics.toml"
        else:
            data_string = service.create_rubric_template(
                question_index=question, filetype="csv"
            )
            buf3 = StringIO(data_string)
            response = HttpResponse(buf3.getvalue(), content_type="text/csv")
            response["Content-Disposition"] = "attachment; filename=rubrics.csv"
        return response


class RubricCreateView(ManagerRequiredView):
    """Handles the creation of new rubrices."""

    def post(self, request: HttpRequest) -> HttpResponse:
        """Posting from a form to the rubric creator makes a new rubric."""
        form = RubricItemForm(request.POST)
        if not form.is_valid():
            messages.error(request, f"invalid form data: {form.errors}")
            return redirect("rubrics_landing")
        rubric_data = {
            "user": request.user.pk,
            "modified_by_user": request.user.pk,
            "text": form.cleaned_data["text"],
            "kind": form.cleaned_data["kind"],
            "value": form.cleaned_data["value"],
            "out_of": form.cleaned_data["out_of"],
            "meta": form.cleaned_data["meta"],
            "question_index": form.cleaned_data["question_index"],
            "versions": form.cleaned_data["versions"],
            "parameters": form.cleaned_data["parameters"],
            "tags": form.cleaned_data["tags"],
            "pedagogy_tags": form.cleaned_data["pedagogy_tags"],
            "published": form.cleaned_data["published"],
        }
        try:
            RubricService.create_rubric(rubric_data, creating_user=request.user)
        except (ValueError, PermissionDenied) as e:
            messages.error(request, f"Error: {e}")
        except serializers.ValidationError as e:
            # see comments elsewhere about formatting serializer.ValidationError
            (nicer_err_msgs,) = e.args
            messages.error(request, f"Error: {nicer_err_msgs}")
        else:
            messages.success(request, "Rubric created successfully.")

        return redirect("rubrics_landing")


class RubricEditView(ManagerRequiredView):
    """Handles the editing of existing rubrices."""

    def post(self, request: HttpRequest, *, rid: int) -> HttpResponse:
        """Posting from a form to edit an existing rubric."""
        # TODO: am I supposed to do this through the form?
        tag_tasks = request.POST.get("tag_tasks") == "on"
        minor_change = request.POST.get("minor_change")
        if minor_change is None or minor_change == "auto":
            is_minor_change = None
        elif minor_change == "yes":
            is_minor_change = True
        elif minor_change == "no":
            is_minor_change = False
        else:
            messages.error(request, "invalid form choices for minor radios")
            return redirect("rubric_item", rid)

        form = RubricItemForm(request.POST)
        if not form.is_valid():
            messages.error(request, f"invalid form data: {form.errors}")
            return redirect("rubric_item", rid)
        rubric = RubricService.get_rubric_by_rid(rid)
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
            "subrevision": rubric.subrevision,
            "tags": form.cleaned_data["tags"],
            "pedagogy_tags": form.cleaned_data["pedagogy_tags"],
            "published": form.cleaned_data["published"],
        }
        try:
            RubricService.modify_rubric(
                rid,
                rubric_data,
                modifying_user=User.objects.get(username=request.user.username),
                tag_tasks=tag_tasks,
                is_minor_change=is_minor_change,
            )
        except (ValueError, PermissionDenied, PlomConflict) as e:
            messages.error(request, f"Error: {e}")
        except serializers.ValidationError as e:
            # see comments elsewhere about formatting serializer.ValidationError
            (nicer_err_msgs,) = e.args
            messages.error(request, f"Error: {nicer_err_msgs}")
        else:
            messages.success(request, "Rubric edited successfully.")

        return redirect("rubric_item", rid)
