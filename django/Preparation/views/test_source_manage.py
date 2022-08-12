from django import forms
from django.core.exceptions import ObjectDoesNotExist
from django.http import FileResponse, Http404
from django.shortcuts import render
from django_htmx.http import HttpResponseClientRedirect

# TODO - replace these functions with real ones

from Preparation.services.temp_functions import (
    how_many_test_versions,
    how_many_test_pages,
)
from Preparation.services import TestSourceService
from Preparation.views.needs_manager_view import ManagerRequiredBaseView


class TestSourceUploadForm(forms.Form):
    pdf_file = forms.FileField(
        label="",
        widget=forms.FileInput(attrs={"accept": ".pdf"}),
    )


class TestSourceManageView(ManagerRequiredBaseView):
    def build_context(self):
        tss = TestSourceService()

        return {
            "form": TestSourceUploadForm(),
            "test_versions": how_many_test_versions(),
            "number_test_sources_uploaded": tss.how_many_test_versions_uploaded(),
            "number_of_pages": how_many_test_pages(),
            "uploaded_test_sources": tss.get_list_of_sources(),
            "all_test_sources_uploaded": tss.are_all_test_versions_uploaded(),
            "duplicates": tss.check_pdf_duplication(),
        }

    def get(self, request, version=None):
        if version:
            tss = TestSourceService()
            try:
                source_path = tss.get_source_pdf_path(version)
                return FileResponse(
                    open(source_path, "rb"),
                    as_attachment=True,
                    filename=f"source{version}.pdf",
                )
            except ObjectDoesNotExist:
                raise Http404("No such file")

        else:
            context = self.build_context()
            return render(request, "Preparation/test_source_manage.html", context)

    def post(self, request, version=None):
        if not request.FILES["source_pdf"]:
            context = {"success": False, "message": "Form invalid", "version": version}
        else:
            tss = TestSourceService()
            success, message = tss.take_source_from_upload(
                version, how_many_test_pages(), request.FILES["source_pdf"]
            )
            context = {"version": version, "success": success, "message": message}

        return render(request, "Preparation/test_source_attempt.html", context)

    def delete(self, request, version=None):
        if version:
            tss = TestSourceService()
            tss.delete_test_source(version)
        return HttpResponseClientRedirect("/preparation/test_source")
