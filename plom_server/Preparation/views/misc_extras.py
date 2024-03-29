# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2023 Colin B. Macdonald

from django.urls import reverse
from django.shortcuts import render
from django.http import FileResponse
from django_htmx.http import HttpResponseClientRedirect

from Base.base_group_views import ManagerRequiredView
from ..services import ExtraPageService, ScrapPaperService


class MiscExtrasView(ManagerRequiredView):
    def get(self, request):
        ep_service = ExtraPageService()
        sp_service = ScrapPaperService()
        context = self.build_context()
        context.update(
            {
                "extra_page_task_status": ep_service.get_extra_page_task_status(),
                "scrap_paper_task_status": sp_service.get_scrap_paper_task_status(),
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


class ScrapPaperView(ManagerRequiredView):
    def get(self, request):
        sp_service = ScrapPaperService()
        return FileResponse(
            open(sp_service.get_scrap_paper_pdf_filepath(), "rb"),
            as_attachment=True,
            filename="scrap_paper.pdf",
        )

    def put(self, request):
        sp_service = ScrapPaperService()
        sp_service.build_scrap_paper_pdf()
        return HttpResponseClientRedirect(reverse("misc_extras"))

    def delete(self, request):
        sp_service = ScrapPaperService()
        sp_service.delete_scrap_paper_pdf()
        return HttpResponseClientRedirect(reverse("misc_extras"))
