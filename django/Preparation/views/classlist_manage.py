from braces.views import GroupRequiredMixin
from django import forms
from django.http import FileResponse, HttpResponse
from django.shortcuts import render
from django.views import View

from django_htmx.http import HttpResponseClientRedirect

from Preparation.services import (
    StagingClasslistCSVService,
    StagingStudentService,
    PrenameSettingService,
)


class ClasslistDownloadView(View):
    # group_required = [u"manager"]
    def get(self, request):
        pss = PrenameSettingService()
        sss = StagingStudentService()
        csv_txt = sss.get_students_as_csv_string(prename=pss.get_prenaming_setting())
        return HttpResponse(csv_txt, content_type="text/plain")


class ClasslistDeleteView(View):
    # group_required = [u"manager"]
    def delete(self, request):
        # delete both the csvfile and the classlist of students
        sss = StagingStudentService()
        sss.remove_all_students()

        scsv = StagingClasslistCSVService()
        scsv.delete_classlist_csv()
        return HttpResponseClientRedirect(".")


class ClasslistView(View):
    # group_required = [u"manager"]

    def get(self, request):
        sss = StagingStudentService()
        pss = PrenameSettingService()

        context = {
            "student_list_present": sss.are_there_students(),
            "student_list": sss.get_students(),
            "prenaming": pss.get_prenaming_setting(),
        }
        return render(request, "Preparation/classlist_manage.html", context)

    def post(self, request):
        if not request.FILES["classlist_csv"]:
            return HttpResponseClientRedirect(".")

        scsv = StagingClasslistCSVService()
        success, warn_err = scsv.take_classlist_from_upload(
            request.FILES["classlist_csv"]
        )
        context = {"success": success, "warn_err": warn_err}
        return render(request, "Preparation/classlist_attempt.html", context)

    def delete(self, request):
        scsv = StagingClasslistCSVService()
        scsv.delete_classlist_csv()
        return HttpResponseClientRedirect(".")

    def put(self, request):
        sss = StagingStudentService()
        sss.use_classlist_csv()
        return HttpResponseClientRedirect(".")
