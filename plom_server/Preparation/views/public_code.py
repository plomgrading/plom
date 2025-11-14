# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Colin B. Macdonald

from django.http import (
    HttpRequest,
    HttpResponse,
    HttpResponseBadRequest,
)
from django.shortcuts import render, redirect

from plom.tpv_utils import new_magic_code
from plom_server.Base.services import Settings
from plom_server.Base.base_group_views import ManagerRequiredView


class PublicCodeView(ManagerRequiredView):
    """Views to see or set the public code."""

    def get(self, request: HttpRequest) -> HttpResponse:
        """Get to render a page showing the current code and a form to change it."""
        public_code = Settings.get_public_code()
        context = self.build_context()
        context.update({"public_code": public_code})
        return render(request, "Preparation/public_code.html", context)

    def post(self, request: HttpRequest) -> HttpResponse:
        """Posting will change the public code to the "new_public_code" field.

        Posting a blank new_public_code will choose a new random one.
        """
        public_code = request.POST.get("new_public_code")
        if not request.POST.get("confirm_check"):
            return HttpResponseBadRequest("Must confirm by clicking the checkbox")
        if not public_code:
            public_code = new_magic_code()
        try:
            Settings.set_public_code(public_code)
        except ValueError as e:
            return HttpResponseBadRequest(e)
        return redirect("public_code")
