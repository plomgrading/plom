from braces.views import GroupRequiredMixin
from django import forms
from django.http import FileResponse
from django.shortcuts import render
from django.views import View

from django_htmx.http import HttpResponseClientRedirect


from Preparation.services import PrenameClasslistCSVService, PrenameStudentService, PrenameSettingService


class ClasslistDownloadView(View):
    # group_required = [u"manager"]
    def get(self, request):
        pcsv = PrenameClasslistCSVService()
        csv_path = pcsv.get_classlist_csv_filepath()
        return FileResponse(
            open(csv_path, 'rb'),
            as_attachment=True,
            filename="classlist.csv",
        )


class ClasslistDeleteView(View):
    # group_required = [u"manager"]
    def delete(self, request):
        # delete both the csvfile and the classlist of students
        pss = PrenameStudentService()
        pss.remove_all_students()
        
        pcsv = PrenameClasslistCSVService()
        pcsv.delete_classlist_csv()
        return HttpResponseClientRedirect(".")


class ClasslistView(View):
    # group_required = [u"manager"]

    def get(self, request):
        pstd = PrenameStudentService()
        pss = PrenameSettingService()
        
        context = {
            "std_list_present": pstd.are_there_students(),
            "student_list": pstd.get_students(),
            "prenaming": pss.get_prenaming_setting()
        }
        return render(request, "Preparation/classlist_manage.html", context)

    def post(self, request):
        if not request.FILES["classlist_csv"]:
            return HttpResponseClientRedirect(".")

        pcsv = PrenameClasslistCSVService()
        success, warn_err = pcsv.take_classlist_from_upload(
            request.FILES["classlist_csv"]
        )
        context = {"success": success, "warn_err": warn_err}
        return render(request, "Preparation/classlist_attempt.html", context)

    def delete(self, request):
        pcsv = PrenameClasslistCSVService()
        pcsv.delete_classlist_csv()
        return HttpResponseClientRedirect(".")

    def put(self, request):
        pss = PrenameStudentService()
        pss.use_classlist_csv()
        return HttpResponseClientRedirect(".")

