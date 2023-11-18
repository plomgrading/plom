# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Andrew Rechnitzer
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2022-2023 Colin B. Macdonald

from pathlib import Path
import tempfile

from django.shortcuts import render, redirect
from django.http import HttpResponseRedirect, HttpResponse
from django_htmx.http import HttpResponseClientRedirect

from Base.base_group_views import ManagerRequiredView
from Papers.services import SpecificationService

from plom.misc_utils import format_int_list_with_runs

from ..services import (
    PQVMappingService,
    PrenameSettingService,
    StagingStudentService,
    TestPreparedSetting,
)

from plom.version_maps import version_map_from_file


class PQVMappingUploadView(ManagerRequiredView):
    def get(self, request):
        # if you are here, then you should really be at the main qvmap management page.
        return redirect("prep_qvmapping")

    def post(self, request):
        if not request.FILES["pqvmap_csv"]:
            return redirect("prep_qvmapping")

        # if there is already a qv map redirect
        if PQVMappingService().is_there_a_pqv_map():
            return redirect("prep_qvmapping")

        prenamed_papers = list(StagingStudentService().get_prenamed_papers().keys())

        context = {"errors": []}
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

        context["min_number_to_produce"] = sss.get_minimum_number_to_produce()

        if context["pqv_mapping_present"]:
            context["pqv_table"] = pqvs.get_pqv_map_as_table(
                prenaming=context["prenaming"]
            )
            context["pqv_number_rows"] = len(context["pqv_table"])

        return context

    def get(self, request):
        if TestPreparedSetting.is_test_prepared():
            return redirect("prep_qvmapping_view")
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
