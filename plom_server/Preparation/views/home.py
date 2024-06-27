# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2024 Andrew Rechnitzer
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2024 Colin B. Macdonald

from django.http import HttpResponse, HttpRequest
from django.shortcuts import render
from django.urls import reverse
from django_htmx.http import HttpResponseClientRefresh, HttpResponseClientRedirect

from django.contrib.messages import get_messages

from Base.base_group_views import ManagerRequiredView
from BuildPaperPDF.services import BuildPapersService
from Papers.services import (
    SpecificationService,
    PaperInfoService,
)
from ..services import (
    SourceService,
    PrenameSettingService,
    StagingStudentService,
    PQVMappingService,
    ExtraPageService,
    ScrapPaperService,
    PapersPrinted,
)


class PreparationLandingView(ManagerRequiredView):
    def build_context(self):
        pss = PrenameSettingService()
        sss = StagingStudentService()
        pqvs = PQVMappingService()
        bps = BuildPapersService()
        pinfo = PaperInfoService()

        context = {
            "num_uploaded_source_versions": SourceService.how_many_source_versions_uploaded(),
            "all_sources_uploaded": SourceService.are_all_sources_uploaded(),
            "prename_enabled": pss.get_prenaming_setting(),
            "can_qvmap": False,
            "student_list_present": sss.are_there_students(),
            "papers_staged": pinfo.is_paper_database_populated(),
            "papers_built": bps.are_all_papers_built(),
            "extra_page_status": ExtraPageService().get_extra_page_task_status(),
            "scrap_paper_status": ScrapPaperService().get_scrap_paper_task_status(),
            "have_papers_been_printed": PapersPrinted.have_papers_been_printed(),
            "can_unset_papers_printed": PapersPrinted.can_status_be_set_false(),
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

        if SpecificationService.is_there_a_spec():
            context.update(
                {
                    "valid_spec": True,
                    "can_upload_source_tests": True,
                    "can_qvmap": True,
                    "spec_longname": SpecificationService.get_longname(),
                    "spec_shortname": SpecificationService.get_shortname(),
                    "slugged_spec_shortname": SpecificationService.get_short_name_slug(),
                    "num_versions": SpecificationService.get_n_versions(),
                }
            )
        else:
            context.update(
                {
                    "valid_spec": False,
                    "can_upload_source_tests": False,
                    "num_versions": 0,
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

    def get(self, request: HttpRequest) -> HttpResponse:
        context = self.build_context()
        return render(request, "Preparation/home.html", context)


class PreparationDependencyConflictView(ManagerRequiredView):
    """This view is used to display a preparation dependency conflict error message to users."""

    def get(self, request: HttpRequest) -> HttpResponse:
        context = self.build_context()
        reasons = []
        for msg in get_messages(request):
            reasons.append(f"{msg}")

        context.update({"reasons": reasons})
        return render(request, "Preparation/dependency_conflict.html", context)


class LandingResetSources(ManagerRequiredView):
    def delete(self, request):
        SourceService.delete_all_source_pdfs()
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
    """Toggle the PapersPrint state. When True, bundles are allowed to be pushed to the server."""

    def post(self, request):
        current_setting = PapersPrinted.have_papers_been_printed()
        try:
            PapersPrinted.set_papers_printed(not current_setting)
        except RuntimeError as e:
            # TODO: uses the troubles-afoot kludge (Issue #3251)
            hint = f"maybe-started-uploads-{e}"
            return HttpResponseClientRedirect(reverse("troubles_afoot", args=[hint]))
        return HttpResponseClientRefresh()
