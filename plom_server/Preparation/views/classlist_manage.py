# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Andrew Rechnitzer
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2023 Colin B. Macdonald

from django.http import HttpResponse
from django.shortcuts import render, redirect

from django_htmx.http import HttpResponseClientRedirect

from ..services import (
    StagingClasslistCSVService,
    StagingStudentService,
    PrenameSettingService,
)

from Base.base_group_views import ManagerRequiredView


class ClasslistDownloadView(ManagerRequiredView):
    def get(self, request):
        pss = PrenameSettingService()
        sss = StagingStudentService()
        csv_txt = sss.get_students_as_csv_string(prename=pss.get_prenaming_setting())
        return HttpResponse(csv_txt, content_type="text/plain")


class ClasslistDeleteView(ManagerRequiredView):
    def delete(self, request):
        # delete both the csvfile and the classlist of students
        sss = StagingStudentService()
        sss.remove_all_students()

        scsv = StagingClasslistCSVService()
        scsv.delete_classlist_csv()
        return HttpResponseClientRedirect(".")


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
        if not request.FILES["classlist_csv"]:
            return HttpResponseClientRedirect(".")

        scsv = StagingClasslistCSVService()

        # if there is already a classlist redirect to the classlist landing page
        if scsv.is_there_a_classlist():
            return redirect("prep_classlist")

        success, warn_err = scsv.take_classlist_from_upload(
            request.FILES["classlist_csv"]
        )
        context.update({"success": success, "warn_err": warn_err})
        return render(request, "Preparation/classlist_attempt.html", context)

    def delete(self, request):
        scsv = StagingClasslistCSVService()
        scsv.delete_classlist_csv()
        return HttpResponseClientRedirect(".")

    def put(self, request):
        sss = StagingStudentService()
        sss.use_classlist_csv()
        return HttpResponseClientRedirect(".")


class ClasslistReadOnlyView(ManagerRequiredView):
    def get(self, request):
        context = self.build_context()
        sss = StagingStudentService()
        pss = PrenameSettingService()

        context.update(
            {
                "prenaming": pss.get_prenaming_setting(),
                "student_list": sss.get_students(),
            }
        )

        return render(request, "Preparation/classlist_view.html", context)
