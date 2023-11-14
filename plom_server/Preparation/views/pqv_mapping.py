# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Andrew Rechnitzer
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2022-2023 Colin B. Macdonald

from pathlib import Path
import tempfile

from django.shortcuts import render, redirect
from django.http import HttpResponseRedirect, HttpResponse
from django_htmx.http import HttpResponseClientRedirect

from Base.base_group_views import ManagerRequiredView
from Papers.services import SpecificationService
from SpecCreator.services import StagingSpecificationService

from ..services import (
    PQVMappingService,
    PrenameSettingService,
    StagingStudentService,
)

from plom.version_maps import version_map_from_file


class PQVMappingUploadView(ManagerRequiredView):
    def get(self, request):
        return redirect("prep_qvmapping")

    def post(self, request):
        if not request.FILES["pqvmap_csv"]:
            return redirect("prep_qvmapping")

        context = {"errors": []}
        # far from ideal, but the csv module doesn't like bytes.
        try:
            with tempfile.TemporaryDirectory() as td:
                f = Path(td) / "file.csv"
                with f.open("wb") as fh:
                    fh.write(request.FILES["pqvmap_csv"].read())
                vm = version_map_from_file(f)
        except ValueError as e:
            context["errors"].append({"kind": "ValueError", "err_text": f"{e}"})
        except KeyError as e:
            context["errors"].append({"kind": "KeyError", "err_text": f"{e}"})

        if context["errors"]:
            return render(request, "Preparation/pqv_mapping_attempt.html", context)

        # if any errors at this point, bail out and report them

        try:
            PQVMappingService().use_pqv_map(vm)
        except ValueError as e:
            context["errors"].append({"kind": "ValueError", "err_text": f"{e}"})

        if context["errors"]:
            return render(request, "Preparation/pqv_mapping_attempt.html", context)

        # all successful, so return to the main pqvmapping-management page
        return redirect("prep_qvmapping")


class PQVMappingDownloadView(ManagerRequiredView):
    def get(self, request):
        pqvs = PQVMappingService()
        pqvs_csv_txt = pqvs.get_pqv_map_as_csv_string()
        return HttpResponse(pqvs_csv_txt, content_type="text/plain")


class PQVMappingDeleteView(ManagerRequiredView):
    def delete(self, request):
        pqvs = PQVMappingService()
        pqvs.remove_pqv_map()
        return HttpResponseClientRedirect(".")


class PQVMappingView(ManagerRequiredView):
    def build_context(self):
        pqvs = PQVMappingService()
        pss = PrenameSettingService()
        sss = StagingStudentService()

        context = {
            "number_of_questions": SpecificationService.get_n_questions(),
            "question_list": range(1, 1 + SpecificationService.get_n_questions()),
            "prenaming": pss.get_prenaming_setting(),
            "pqv_mapping_present": pqvs.is_there_a_pqv_map(),
            "number_of_students": sss.how_many_students(),
            "student_list_present": sss.are_there_students(),
            "navbar_colour": "#AD9CFF",
            "user_group": "manager",
        }
        fpp, lpp = sss.get_first_last_prenamed_paper()
        context.update({"first_prenamed_paper": fpp, "last_prenamed_paper": lpp})

        context["min_number_to_produce"] = sss.get_minimum_number_to_produce()

        if context["pqv_mapping_present"]:
            context["pqv_table"] = pqvs.get_pqv_map_as_table(
                prenaming=context["prenaming"]
            )
            context["pqv_number_rows"] = len(context["pqv_table"])

        return context

    def get(self, request):
        context = self.build_context()
        return render(request, "Preparation/pqv_mapping_manage.html", context)

    def post(self, request):
        ntp = request.POST.get("number_to_produce", None)
        if not ntp:
            return HttpResponseRedirect(".")
        try:
            number_to_produce = int(ntp)
        except ValueError:
            return HttpResponseRedirect(".")

        pqvs = PQVMappingService()
        pqvs.generate_and_set_pqvmap(number_to_produce)
        return HttpResponseRedirect(".")


class PQVMappingReadOnlyView(ManagerRequiredView):
    def build_context(self):
        context = super().build_context()
        pqvs = PQVMappingService()
        pss = PrenameSettingService()

        context.update(
            {
                "prenaming": pss.get_prenaming_setting(),
                "question_list": range(1, 1 + SpecificationService.get_n_questions()),
                "pqv_table": pqvs.get_pqv_map_as_table(pss.get_prenaming_setting()),
            }
        )
        return context

    def get(self, request):
        context = self.build_context()
        return render(request, "Preparation/pqv_mapping_view.html", context)
