from braces.views import GroupRequiredMixin
from django import forms
from django.http import FileResponse
from django.shortcuts import render
from django.views import View

from django_htmx.http import HttpResponseClientRedirect

from Preparation.views.needs_manager_view import ManagerRequiredBaseView

from Preparation.services.temp_functions import (
    is_there_a_valid_spec,
    can_I_prename,
    can_I_upload_source_tests,
    can_I_qvmap,
    are_all_source_tests_uploaded,
    how_many_test_versions,
    how_many_test_versions_uploaded,
)

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
            "valid_spec": is_there_a_valid_spec(),
            "test_versions": how_many_test_versions(),
            "uploaded_test_versions": tss.how_many_test_versions_uploaded(),
            "can_upload_source_tests": can_I_upload_source_tests(),
            "all_source_tests_uploaded": tss.are_all_test_versions_uploaded(),
            "can_prename": can_I_prename(),
            "prename_enabled": pss.get_prenaming_setting(),
            "can_qvmap": can_I_qvmap(),
            "student_list_present": sss.are_there_students(),
            "server_valid": cpsi.is_server_info_valid(),
            "password_valid": cpsi.is_password_valid(),
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

        return context

    def get(self, request):
        context = self.build_context()
        return render(request, "Preparation/home.html", context)
