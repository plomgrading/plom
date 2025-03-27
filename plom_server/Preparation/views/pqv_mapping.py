# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Andrew Rechnitzer
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2022-2025 Colin B. Macdonald

import tempfile
from io import BytesIO
from pathlib import Path
from typing import Any

from django.shortcuts import render, redirect
from django.http import FileResponse, HttpRequest, HttpResponseRedirect, HttpResponse
from django.urls import reverse
from django_htmx.http import HttpResponseClientRedirect
from django.contrib import messages

from plom_server.Base.base_group_views import ManagerRequiredView
from plom_server.Papers.services import (
    SpecificationService,
    PaperCreatorService,
    PaperInfoService,
)

from plom.misc_utils import format_int_list_with_runs
from plom.plom_exceptions import PlomDependencyConflict, PlomDatabaseCreationError

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

        # if database is populated then redirect
        if PaperInfoService.is_paper_database_populated():
            return redirect("prep_qvmapping")

        prenamed_papers = list(StagingStudentService.get_prenamed_papers().keys())
        num_questions = SpecificationService.get_n_questions()
        num_versions = SpecificationService.get_n_versions()

        context: dict[str, Any] = {"errors": []}
        # far from ideal, but the csv module doesn't like bytes.
        try:
            with tempfile.TemporaryDirectory() as td:
                f = Path(td) / "file.csv"
                with f.open("wb") as fh:
                    fh.write(request.FILES["pqvmap_csv"].read())
                # this function also validates the version map
                vm = version_map_from_file(
                    f,
                    required_papers=prenamed_papers,
                    num_questions=num_questions,
                    num_versions=num_versions,
                )
        except ValueError as e:
            context["errors"].append({"kind": "ValueError", "err_text": f"{e}"})
        except KeyError as e:
            context["errors"].append({"kind": "KeyError", "err_text": f"{e}"})
        # if any errors at this point, bail out and report them
        if context["errors"]:
            return render(request, "Preparation/pqv_mapping_attempt.html", context)

        try:
            PaperCreatorService.add_all_papers_in_qv_map(vm)
        except PlomDependencyConflict as err:
            messages.add_message(request, messages.ERROR, f"{err}")
            return HttpResponseClientRedirect(reverse("prep_conflict"))

        # all successful, so return to the main pqvmapping-management page
        return redirect("prep_qvmapping")


class PQVMappingDownloadView(ManagerRequiredView):
    """Download the question-version map as a csv file."""

    def get(self, request: HttpRequest) -> HttpResponse | FileResponse:
        """Get method to download the question-version map as a csv file."""
        try:
            pqvs_csv_txt = PQVMappingService.get_pqv_map_as_csv_string()
        except ValueError as err:  # triggered by empty qv-map
            messages.add_message(request, messages.ERROR, f"{err}")
            # redirect here (not htmx) since this is called by normal http
            return redirect(reverse("prep_conflict"))

        # Note: without BytesIO here it doesn't respect filename, get "download.csv"
        return FileResponse(
            BytesIO(pqvs_csv_txt.encode("utf-8")),
            content_type="text/csv; charset=UTF-8",
            filename=PQVMappingService.get_default_csv_filename(),
            as_attachment=True,
        )


class PQVMappingDeleteView(ManagerRequiredView):
    """Used to trigger a delete of the qv-map and the papers in the database."""

    def delete(self, request: HttpRequest) -> HttpResponse:
        try:
            PaperCreatorService.remove_all_papers_from_db()
        except PlomDependencyConflict as err:
            messages.add_message(request, messages.ERROR, f"{err}")
            return HttpResponseClientRedirect(reverse("prep_conflict"))
        except PlomDatabaseCreationError:
            # return to qvmap page since it will display a message with
            # info about what is happening to the db
            return HttpResponseClientRedirect(reverse("prep_qvmapping"))

        return HttpResponseClientRedirect(reverse("prep_qvmapping"))


class PQVMappingView(ManagerRequiredView):
    def build_context(self) -> dict[str, Any]:
        """Retrieve various information related to papers in DB."""
        if not SpecificationService.is_there_a_spec():
            raise PlomDependencyConflict(
                "DB papers cannot be created before the assessment specification."
            )

        triples = SpecificationService.get_question_html_label_triples()
        question_indices = [t[0] for t in triples]
        fixshuf = SpecificationService.get_selection_method_of_all_questions()
        labels_fix = ", ".join(t[2] for t in triples if fixshuf[t[0]] == "fix")
        labels_shf = ", ".join(t[2] for t in triples if fixshuf[t[0]] == "shuffle")

        num_students = StagingStudentService().how_many_students()

        context = {
            "question_indices": question_indices,
            "question_labels_html": triples,
            "question_labels_html_fix": labels_fix,
            "question_labels_html_shuffle": labels_shf,
            "prenaming": PrenameSettingService().get_prenaming_setting(),
            "pqv_mapping_present": PaperInfoService.is_paper_database_fully_populated(),
            "number_of_students": num_students,
            "number_plus_twenty": num_students + 20,
            "number_times_1dot1": (num_students * 11) // 10,
            "student_list_present": StagingStudentService().are_there_students(),
            "have_papers_been_printed": PapersPrinted.have_papers_been_printed(),
            "chore_status": PaperCreatorService.get_chore_status(),
            "chore_message": PaperCreatorService.get_chore_message(),
            "populate_in_progress": PaperCreatorService.is_populate_in_progress(),
            "evacuate_in_progress": PaperCreatorService.is_evacuate_in_progress(),
        }

        prenamed_papers_list = list(StagingStudentService.get_prenamed_papers().keys())

        if prenamed_papers_list:
            context.update(
                {
                    "prenamed_papers_list": format_int_list_with_runs(
                        prenamed_papers_list
                    ),
                    "first_prenamed_paper": min(prenamed_papers_list),
                    "last_prenamed_paper": max(prenamed_papers_list),
                    "last_plus_ten": max(prenamed_papers_list) + 10,
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
        """Render page for paper DB and qvmap management."""
        try:
            context = self.build_context()
        except PlomDependencyConflict as err:
            messages.add_message(request, messages.ERROR, f"{err}")
            return redirect(reverse("prep_conflict"))

        return render(request, "Preparation/pqv_mapping_manage.html", context)

    def post(self, request: HttpRequest) -> HttpResponse:
        """Populate DB with papers."""
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
            vm = PQVMappingService().make_version_map(number_to_produce, first=first)
            PaperCreatorService.add_all_papers_in_qv_map(vm)
        except PlomDependencyConflict as err:
            messages.add_message(request, messages.ERROR, f"{err}")
            return HttpResponseClientRedirect(reverse("prep_conflict"))
        except PlomDatabaseCreationError:
            # refresh the page since it will display a message with
            # info about what is happening to the db
            return HttpResponseRedirect(".")

        return HttpResponseRedirect(".")
