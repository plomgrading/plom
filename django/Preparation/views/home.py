from braces.views import GroupRequiredMixin
from django import forms
from django.http import FileResponse
from django.shortcuts import render
from django.views import View

from django_htmx.http import HttpResponseClientRedirect

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
)


# Create your views here.
class PreparationLandingView(View):
    # group_required = [u"manager"]
    def build_context(self):
        tss = TestSourceService()
        pss = PrenameSettingService()
        sss = StagingStudentService()
        return {
            "valid_spec": is_there_a_valid_spec(),
            "test_versions": how_many_test_versions(),
            "uploaded_test_versions": tss.how_many_test_versions_uploaded(),
            "can_upload_source_tests": can_I_upload_source_tests(),
            "all_source_tests_uploaded": tss.are_all_test_versions_uploaded(),
            "can_prename": can_I_prename(),
            "prename_enabled": pss.get_prenaming_setting(),
            "can_qvmap": can_I_qvmap(),
            "student_list_present": sss.are_there_students()
        }

    def get(self, request):
        context = self.build_context()
        return render(request, "Preparation/home.html", context)
