from django.urls import reverse

from django.shortcuts import render
from django.http import FileResponse
from django_htmx.http import HttpResponseClientRedirect

from Preparation.services import ExtraPageService
from Base.base_group_views import ManagerRequiredView


class MiscExtrasView(ManagerRequiredView):
    def get(self, request):
        eps = ExtraPageService()
        context = self.build_context()
        context.update(
            {
                "extra_page_present": eps.is_there_an_extra_page_pdf(),
            }
        )
        return render(request, "Preparation/misc_extras.html", context)


class ExtraPageView(ManagerRequiredView):
    def get(self, request):
        eps = ExtraPageService()
        source_path = eps.get_extra_page_pdf_filepath()
        return FileResponse(
            open(source_path, "rb"),
            as_attachment=True,
            filename="extra_page.pdf",
        )

    def put(self, request):
        eps = ExtraPageService()
        eps.build_extra_page_pdf()
        return HttpResponseClientRedirect(reverse("misc_extras"))

    def delete(self, request):
        eps = ExtraPageService()
        eps.delete_extra_page_pdf()
        return HttpResponseClientRedirect(reverse("misc_extras"))
