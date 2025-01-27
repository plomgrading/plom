# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2024 Andrew Rechnitzer
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2023, 2025 Colin B. Macdonald

from io import BytesIO

from django.http import FileResponse, HttpRequest, HttpResponse
from django.shortcuts import render, redirect
from django.urls import reverse
from django.contrib import messages

from django_htmx.http import HttpResponseClientRedirect

from ..services import StagingStudentService, PrenameSettingService, PapersPrinted

from Base.base_group_views import ManagerRequiredView
from plom.plom_exceptions import PlomDependencyConflict


class ClasslistDownloadView(ManagerRequiredView):
    """Download the classlist."""

    def get(self, request: HttpRequest) -> FileResponse:
        """Get method to download the classlist as a csv file.

        The file is utf-8 encoded.  Note: The internet has many comments
        about MS Excel and BOM.  Do we need to keep that software happy?
        """
        pss = PrenameSettingService()
        sss = StagingStudentService()
        csv_txt = sss.get_students_as_csv_string(prename=pss.get_prenaming_setting())
        # Note: without BytesIO here it doesn't respect filename, get "download.csv"
        return FileResponse(
            BytesIO(csv_txt.encode("utf-8")),
            content_type="text/csv; charset=UTF-8",
            filename="classlist.csv",
            as_attachment=True,
        )


class ClasslistView(ManagerRequiredView):
    def get(self, request: HttpRequest) -> HttpResponse:
        sss = StagingStudentService()
        pss = PrenameSettingService()

        context = self.build_context()
        context.update(
            {
                "student_list_present": sss.are_there_students(),
                "student_list": sss.get_students(),
                "prenaming": pss.get_prenaming_setting(),
                "have_papers_been_printed": PapersPrinted.have_papers_been_printed(),
            }
        )
        return render(request, "Preparation/classlist_manage.html", context)

    def post(self, request: HttpRequest) -> HttpResponse:
        # NOTE - regular http post, not htmx
        context = self.build_context()
        ignore_warnings = request.POST.get("ignoreWarnings", False)

        if not request.FILES["classlist_csv"]:
            return redirect("prep_classlist")

        # check if there are already students in the list.
        sss = StagingStudentService()
        if sss.are_there_students():
            return redirect("prep_classlist")

        try:
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
        except PlomDependencyConflict as err:
            messages.add_message(request, messages.ERROR, f"{err}")
            return redirect("prep_conflict")

    def delete(self, request: HttpRequest) -> HttpResponseClientRedirect:
        # is htmx-delete, not http.
        try:
            StagingStudentService().remove_all_students()
        except PlomDependencyConflict as err:
            messages.add_message(request, messages.ERROR, f"{err}")
            return HttpResponseClientRedirect(reverse("prep_conflict"))
        return HttpResponseClientRedirect(".")
