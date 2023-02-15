from django.urls import reverse

from django.shortcuts import render
from django.http import FileResponse
from django_htmx.http import HttpResponseClientRedirect

from Preparation.services import ExtraPageService
from Base.base_group_views import ManagerRequiredView


class MiscExtrasView(ManagerRequiredView):
    def get(self, request):
        ep_service = ExtraPageService()
        context = self.build_context()
        context.update(
            {
                "extra_page_task_status": ep_service.get_extra_page_task_status(),
            }
        )
        return render(request, "Preparation/misc_extras.html", context)


class ExtraPageView(ManagerRequiredView):
    def get(self, request):
        ep_service = ExtraPageService()
        return FileResponse(
            open(ep_service.get_extra_page_pdf_filepath(), "rb"),
            as_attachment=True,
            filename="extra_page.pdf",
        )

    def put(self, request):
        ep_service = ExtraPageService()
        ep_service.build_extra_page_pdf()
        return HttpResponseClientRedirect(reverse("misc_extras"))

    def delete(self, request):
        ep_service = ExtraPageService()
        ep_service.delete_extra_page_pdf()
        return HttpResponseClientRedirect(reverse("misc_extras"))
