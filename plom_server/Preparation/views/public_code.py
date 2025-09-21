# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Colin B. Macdonald

from django.http import (
    HttpRequest,
    HttpResponse,
    HttpResponseBadRequest,
)
from django.shortcuts import render, redirect

# from django_htmx.http import HttpResponseClientRedirect

from plom_server.Base.base_group_views import ManagerRequiredView
from plom_server.Papers.services import SpecificationService


class PublicCodeView(ManagerRequiredView):
    def get(self, request: HttpRequest) -> HttpResponse:
        # private_code = SpecificationService.get_private_seed()
        # print(private_code)
        public_code = SpecificationService.get_public_code()
        print(public_code)

        context = self.build_context()
        context.update({"public_code": public_code})
        return render(request, "Preparation/public_code.html", context)

    def post(self, request: HttpRequest) -> HttpResponse:
        public_code = request.POST.get("new_public_code")
        if not request.POST.get("confirm_check"):
            return HttpResponseBadRequest("Must confirm by clicking the checkbox")
        SpecificationService.set_public_code(public_code)
        # HTMX?
        # return HttpResponseClientRedirect(reverse("public_code"))
        return redirect("public_code")
        # public_code = SpecificationService.get_public_code()
        # context = self.build_context()
        # context.update({"public_code": public_code})
        # return render(request, "Preparation/public_code.html", context)
