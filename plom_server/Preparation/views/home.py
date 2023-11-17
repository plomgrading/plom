# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Andrew Rechnitzer
# Copyright (C) 2022-2023 Edith Coates

from django.shortcuts import render
from django_htmx.http import HttpResponseClientRefresh

from Base.base_group_views import ManagerRequiredView
from BuildPaperPDF.services import BuildPapersService
from Papers.services import (
    SpecificationService,
    PaperInfoService,
)
from SpecCreator.services import StagingSpecificationService

from ..services import (
    TestSourceService,
    PrenameSettingService,
    StagingStudentService,
    PQVMappingService,
    ExtraPageService,
    ScrapPaperService,
    TestPreparedSetting,
)


class PreparationLandingView(ManagerRequiredView):
    def build_context(self):
        tss = TestSourceService()
        pss = PrenameSettingService()
        sss = StagingStudentService()
        pqvs = PQVMappingService()
        bps = BuildPapersService()
        pinfo = PaperInfoService()

        context = {
            "uploaded_test_versions": tss.how_many_test_versions_uploaded(),
            "all_source_tests_uploaded": tss.are_all_test_versions_uploaded(),
            "prename_enabled": pss.get_prenaming_setting(),
            "can_qvmap": False,
            "student_list_present": sss.are_there_students(),
            "papers_staged": pinfo.is_paper_database_populated(),
            "papers_built": bps.are_all_papers_built(),
            "navbar_colour": "#AD9CFF",
            "user_group": "manager",
            "extra_page_status": ExtraPageService().get_extra_page_task_status(),
            "scrap_paper_status": ScrapPaperService().get_scrap_paper_task_status(),
            "is_test_prepared": TestPreparedSetting.is_test_prepared(),
            "can_status_be_set_todo": TestPreparedSetting.can_status_be_set_false(),
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

        spec = StagingSpecificationService()
        if SpecificationService.is_there_a_spec():
            context.update(
                {
                    "valid_spec": True,
                    "can_upload_source_tests": True,
                    "can_qvmap": True,
                    "spec_longname": spec.get_long_name(),
                    "spec_shortname": spec.get_short_name(),
                    "slugged_spec_shortname": spec.get_short_name_slug(),
                    "test_versions": spec.get_n_versions(),
                    "is_spec_the_same": spec.compare_spec(
                        SpecificationService.get_the_spec()
                    ),
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

        if pss.get_prenaming_setting() and not sss.are_there_students():
            context.update({"can_build_papers": False})
        elif not pqvs.is_there_a_pqv_map():
            context.update({"can_build_papers": False})
        else:
            context.update({"can_build_papers": True})

        return context

    def get(self, request):
        context = self.build_context()
        return render(request, "Preparation/home.html", context)


class LandingResetSpec(ManagerRequiredView):
    def delete(self, request):
        SpecificationService.remove_spec()

        staging_spec = StagingSpecificationService()
        staging_spec.reset_specification()

        sources_service = TestSourceService()
        sources_service.delete_all_test_sources()

        qv_service = PQVMappingService()
        qv_service.remove_pqv_map()

        return HttpResponseClientRefresh()


class LandingResetSources(ManagerRequiredView):
    def delete(self, request):
        sources_service = TestSourceService()
        sources_service.delete_all_test_sources()
        return HttpResponseClientRefresh()


class LandingPrenameToggle(ManagerRequiredView):
    def post(self, request):
        prename_service = PrenameSettingService()
        curr_state = prename_service.get_prenaming_setting()
        prename_service.set_prenaming_setting(not curr_state)
        return HttpResponseClientRefresh()


class LandingResetClasslist(ManagerRequiredView):
    def delete(self, request):
        students = StagingStudentService()
        students.remove_all_students()
        return HttpResponseClientRefresh()


class LandingResetQVmap(ManagerRequiredView):
    def delete(self, request):
        qv_service = PQVMappingService()
        qv_service.remove_pqv_map()
        return HttpResponseClientRefresh()


class LandingFinishedToggle(ManagerRequiredView):
    """Toggle the TestPreparedSetting state. When True, bundles are allowed to be pushed to the server."""

    def post(self, request):
        current_setting = TestPreparedSetting.is_test_prepared()
        TestPreparedSetting.set_test_prepared(not current_setting)
        return HttpResponseClientRefresh()
