from django import forms
from django.core.exceptions import ObjectDoesNotExist
from django.http import FileResponse, Http404
from django.urls import reverse
from django.shortcuts import render
from django_htmx.http import HttpResponseClientRedirect


from Preparation.services import TestSourceService
from SpecCreator.services import TestSpecService

from Base.base_group_views import ManagerRequiredView


class TestSourceUploadForm(forms.Form):
    pdf_file = forms.FileField(
        label="",
        widget=forms.FileInput(attrs={"accept": ".pdf"}),
    )


class TestSourceManageView(ManagerRequiredView):
    def build_context(self):
        tss = TestSourceService()
        speck = TestSpecService()

        return {
            "form": TestSourceUploadForm(),
            "test_versions": speck.get_n_versions(),
            "number_test_sources_uploaded": tss.how_many_test_versions_uploaded(),
            "number_of_pages": speck.get_n_pages(),
            "uploaded_test_sources": tss.get_list_of_sources(),
            "all_test_sources_uploaded": tss.are_all_test_versions_uploaded(),
            "duplicates": tss.check_pdf_duplication(),
            "navbar_colour": "#AD9CFF",
            "user_group": "manager",
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
        context = self.build_context()
        if not request.FILES["source_pdf"]:
            context.update({"success": False, "message": "Form invalid", "version": version})
        else:
            tss = TestSourceService()
            speck = TestSpecService()
            success, message = tss.take_source_from_upload(
                version, speck.get_n_pages(), request.FILES["source_pdf"]
            )
            context.update({"version": version, "success": success, "message": message})

        return render(request, "Preparation/test_source_attempt.html", context)

    def delete(self, request, version=None):
        if version:
            tss = TestSourceService()
            tss.delete_test_source(version)
        return HttpResponseClientRedirect(reverse('prep_sources'))
