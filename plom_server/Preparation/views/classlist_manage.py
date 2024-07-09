# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2024 Andrew Rechnitzer
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2023 Colin B. Macdonald

from django.http import HttpResponse
from django.shortcuts import render, redirect

from django_htmx.http import HttpResponseClientRedirect

from ..services import StagingStudentService, PrenameSettingService

from Base.base_group_views import ManagerRequiredView


class ClasslistDownloadView(ManagerRequiredView):
    def get(self, request):
        pss = PrenameSettingService()
        sss = StagingStudentService()
        csv_txt = sss.get_students_as_csv_string(prename=pss.get_prenaming_setting())
        return HttpResponse(csv_txt, content_type="text/plain")


class ClasslistView(ManagerRequiredView):
    def get(self, request):
        sss = StagingStudentService()
        pss = PrenameSettingService()

        context = self.build_context()
        context.update(
            {
                "student_list_present": sss.are_there_students(),
                "student_list": sss.get_students(),
                "prenaming": pss.get_prenaming_setting(),
            }
        )
        return render(request, "Preparation/classlist_manage.html", context)

    def post(self, request):
        context = self.build_context()
        ignore_warnings = request.POST.get("ignoreWarnings", False)

        if not request.FILES["classlist_csv"]:
            return redirect("prep_classlist")

        # check if there are already students in the list.
        sss = StagingStudentService()
        if sss.are_there_students():
            return HttpResponseClientRedirect(".")

        success, warn_err = sss.validate_and_use_classlist_csv(
            request.FILES["classlist_csv"], ignore_warnings=ignore_warnings
        )
        if (not success) or (warn_err and not ignore_warnings):
            # errors or non-ignorable warnings
            context.update({"success": success, "warn_err": warn_err})
            return render(request, "Preparation/classlist_attempt.html", context)
        else:
            # success!
            return redirect("prep_classlist")

    def delete(self, request):
        # if papers have been printed then redirect to the readonly view

        StagingStudentService().remove_all_students()
        return HttpResponseClientRedirect(".")
