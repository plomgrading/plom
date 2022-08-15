from turtle import update
from braces.views import GroupRequiredMixin
from django import forms
from django.http import FileResponse
from django.shortcuts import render
from django.views import View

from django_htmx.http import HttpResponseClientRedirect

from TestCreator.services import TestSpecService

from Preparation.views.needs_manager_view import ManagerRequiredBaseView

from Preparation.services import (
    TestSourceService,
    PrenameSettingService,
    StagingStudentService,
    PQVMappingService,
    ClassicPlomServerInformationService,
)


# Create your views here.
class PreparationLandingView(ManagerRequiredBaseView):
    def build_context(self):
        tss = TestSourceService()
        pss = PrenameSettingService()
        sss = StagingStudentService()
        pqvs = PQVMappingService()
        cpsi = ClassicPlomServerInformationService()

        context = {
            "uploaded_test_versions": tss.how_many_test_versions_uploaded(),
            "all_source_tests_uploaded": tss.are_all_test_versions_uploaded(),
            "prename_enabled": pss.get_prenaming_setting(),
            "can_qvmap": False,
            "student_list_present": sss.are_there_students(),
            "server_valid": cpsi.is_server_info_valid(),
            "password_valid": cpsi.is_password_valid(),
            "navbar_colour": "#AD9CFF",
            "user_group": "manager",
        }

        paper_number_list = pqvs.list_of_paper_numbers()
        if paper_number_list:
            context.update(
                {
                    "pqv_mapping_present": True,
                    "pqv_number_of_papers": len(paper_number_list),
                    "pqv_first_paper": paper_number_list[0],
                    "pqv_last_paper": paper_number_list[-1],
                }
            )
        else:
            context.update(
                {
                    "pqv_mapping_present": False,
                    "pqv_number_of_papers": 0,
                    "pqv_first_paper": None,
                    "pqv_last_paper": None,
                }
            )

        spec = TestSpecService()
        if spec.is_specification_valid():
            context.update(
                {
                    "valid_spec": True,
                    "can_upload_source_tests": True,
                    "can_qvmap": True,
                    "spec_longname": spec.get_long_name(),
                    "spec_shortname": spec.get_short_name(),
                    "test_versions": spec.get_n_versions(),
                }
            )
        else:
            context.update(
                {
                    "valid_spec": False,
                    "can_upload_source_tests": False,
                    "test_versions": spec.get_n_versions(),
                    "can_qvmap": False,
                }
            )

        return context

    def get(self, request):
        context = self.build_context()
        return render(request, "Preparation/home.html", context)
