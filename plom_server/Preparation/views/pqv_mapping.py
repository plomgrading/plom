# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Andrew Rechnitzer
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2022-2024 Colin B. Macdonald

from __future__ import annotations

from pathlib import Path
import tempfile
from typing import Any

from django.shortcuts import render, redirect
from django.http import HttpRequest, HttpResponseRedirect, HttpResponse
from django.urls import reverse
from django_htmx.http import HttpResponseClientRedirect
from django.contrib import messages

from Base.base_group_views import ManagerRequiredView
from Papers.services import SpecificationService, PaperCreatorService

from plom.misc_utils import format_int_list_with_runs
from plom.plom_exceptions import PlomDependencyConflict

from ..services import (
    PQVMappingService,
    PrenameSettingService,
    StagingStudentService,
    PapersPrinted,
)

from plom.version_maps import version_map_from_file


class PQVMappingUploadView(ManagerRequiredView):
    def get(self, request: HttpRequest) -> HttpResponse:
        # if you are here, then you should really be at the main qvmap management page.
        return redirect("prep_qvmapping")

    def post(self, request: HttpRequest) -> HttpResponse:
        if not request.FILES["pqvmap_csv"]:
            return redirect("prep_qvmapping")

        # if there is already a qv map redirect
        if PQVMappingService().is_there_a_pqv_map():
            return redirect("prep_qvmapping")

        prenamed_papers = list(StagingStudentService().get_prenamed_papers().keys())

        context: dict[str, Any] = {"errors": []}
        # far from ideal, but the csv module doesn't like bytes.
        try:
            with tempfile.TemporaryDirectory() as td:
                f = Path(td) / "file.csv"
                with f.open("wb") as fh:
                    fh.write(request.FILES["pqvmap_csv"].read())
                vm = version_map_from_file(f, required_papers=prenamed_papers)
        except ValueError as e:
            context["errors"].append({"kind": "ValueError", "err_text": f"{e}"})
        except KeyError as e:
            context["errors"].append({"kind": "KeyError", "err_text": f"{e}"})

        if context["errors"]:
            return render(request, "Preparation/pqv_mapping_attempt.html", context)

        # if any errors at this point, bail out and report them

        try:
            PQVMappingService().use_pqv_map(vm)
            PaperCreatorService().add_all_papers_in_qv_map(vm)
        except ValueError as e:
            context["errors"].append({"kind": "ValueError", "err_text": f"{e}"})
        except PlomDependencyConflict as err:
            messages.add_message(request, messages.ERROR, f"{err}")
            return HttpResponseClientRedirect(reverse("prep_conflict"))

        if context["errors"]:
            return render(request, "Preparation/pqv_mapping_attempt.html", context)

        # all successful, so return to the main pqvmapping-management page
        return redirect("prep_qvmapping")


class PQVMappingDownloadView(ManagerRequiredView):
    def get(self, request: HttpRequest) -> HttpResponse:
        pqvs = PQVMappingService()
        pqvs_csv_txt = pqvs.get_pqv_map_as_csv_string()
        return HttpResponse(pqvs_csv_txt, content_type="text/plain")


class PQVMappingDeleteView(ManagerRequiredView):
    """Used to trigger a delete of the qv-map and the papers in the database."""

    def delete(self, request: HttpRequest) -> HttpResponse:
        try:
            PaperCreatorService().remove_all_papers_from_db()
            PQVMappingService().remove_pqv_map()
        except PlomDependencyConflict as err:
            messages.add_message(request, messages.ERROR, f"{err}")
            return HttpResponseClientRedirect(reverse("prep_conflict"))

        return HttpResponseClientRedirect(reverse("prep_qvmapping"))


class PQVMappingView(ManagerRequiredView):
    def build_context(self) -> dict[str, Any]:
        context = {
            "number_of_questions": SpecificationService.get_n_questions(),
            "question_indices": SpecificationService.get_question_indices(),
            "question_labels_html": SpecificationService.get_question_html_label_triples(),
            "fix_questions": SpecificationService.get_fix_questions(),
            "shuffle_questions": SpecificationService.get_shuffle_questions(),
            "prenaming": PrenameSettingService().get_prenaming_setting(),
            "pqv_mapping_present": PQVMappingService().is_there_a_pqv_map(),
            "number_of_students": StagingStudentService().how_many_students(),
            "student_list_present": StagingStudentService().are_there_students(),
            "have_papers_been_printed": PapersPrinted.have_papers_been_printed(),
            "chore_in_progress": PaperCreatorService().is_chore_in_progress(),
            "chore_message": PaperCreatorService().get_chore_message(),
            "populate_in_progress": PaperCreatorService().is_populate_in_progress(),
            "evacuate_in_progress": PaperCreatorService().is_evacuate_in_progress(),
        }

        prenamed_papers_list = list(
            StagingStudentService().get_prenamed_papers().keys()
        )

        if prenamed_papers_list:
            context.update(
                {
                    "prenamed_papers_list": format_int_list_with_runs(
                        prenamed_papers_list
                    ),
                    "last_prenamed_paper": max(prenamed_papers_list),
                }
            )
        else:
            context.update(
                {"prenamed_papers_list": "n/a", "last_prenamed_paper": "n/a"}
            )

        context["min_number_to_produce"] = (
            StagingStudentService().get_minimum_number_to_produce()
        )

        if context["pqv_mapping_present"]:
            context["pqv_table"] = PQVMappingService().get_pqv_map_as_table(
                prenaming=context["prenaming"]
            )
            context["pqv_number_rows"] = len(context["pqv_table"])

        return context

    def get(self, request: HttpRequest) -> HttpResponse:
        context = self.build_context()
        return render(request, "Preparation/pqv_mapping_manage.html", context)

    def post(self, request: HttpRequest) -> HttpResponse:
        ntp = request.POST.get("number_to_produce", None)
        first = request.POST.get("first_paper_num", None)
        if not ntp:
            return HttpResponseRedirect(".")
        if not first:
            first = 1
        if first == "n":
            first = request.POST.get("startn_value", None)

        # TODO neither of these error cases gives a meaningful error message?
        try:
            number_to_produce = int(ntp)
        except ValueError:
            return HttpResponseRedirect(".")
        try:
            first = int(first)
        except ValueError:
            return HttpResponseRedirect(".")

        try:
            PQVMappingService().generate_and_set_pqvmap(number_to_produce, first=first)
            vm = PQVMappingService().get_pqv_map_dict()
            PaperCreatorService().add_all_papers_in_qv_map(vm)
        except PlomDependencyConflict as err:
            messages.add_message(request, messages.ERROR, f"{err}")
            return HttpResponseClientRedirect(reverse("prep_conflict"))

        return HttpResponseRedirect(".")
