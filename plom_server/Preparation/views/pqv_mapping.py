# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Andrew Rechnitzer
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2022-2023 Colin B. Macdonald

from django.shortcuts import render
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


class PQVMappingUploadView(ManagerRequiredView):
    # NOT CURRENTLY BEING USED
    def post(self, request):
        context = {}
        return render(request, "Preparation/pqv_mapping_attempt.html", context)


class PQVMappingDownloadView(ManagerRequiredView):
    def get(self, request):
        pqvs = PQVMappingService()
        pqvs_csv_txt = pqvs.get_pqv_map_as_csv()
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
