# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Colin B. Macdonald
# Copyright (C) 2024 Aden Chan

from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import render, redirect
from django.contrib import messages
from django.views.generic import View
from Base.base_group_views import ManagerRequiredView
from .forms import CompleteWipeForm


class TroublesAfootGenericErrorView(View):
    def get(self, request: HttpRequest, *, hint: str) -> HttpResponse:
        """Render an unexpected or semi-expected "error page" using kludges.

        We'd probably like to show a real error page, like 404 or 500.
        But for technical reasons we might not know how (yet!).
        Code calling this should be improved if possible.

        Args:
            request: the incoming request.

        Keyword Args:
            hint: a short hint about why this is happening.  Its going
                to be recovered from inside the URL so its probably
                something easy to encode like
                ``"oh-snap-x-can-be-negative"``.

        Returns:
            A rendered HTML page.
        """
        context = {"hint": hint}
        return render(request, "base/troubles_afoot.html", context)
    
class ResetView(ManagerRequiredView):
    def get(self, request: HttpRequest) -> HttpResponse:
        return render(request, "base/reset.html")

class ResetConfirmView(ManagerRequiredView):
    def get(self, request: HttpRequest) -> HttpResponse:
        context = self.build_context()
        form = CompleteWipeForm()
        context.update({"wipe_form": form})
        return render(request, "base/reset_confirm.html", context=context)

    def post(self, request: HttpRequest) -> HttpResponse:
        context = self.build_context()
        form = CompleteWipeForm(request.POST)
        reset_phrase = "I wish to completely delete this Plom instance."
        _confirm_field = "confirmation_field"
        if form.is_valid():
            if form.cleaned_data[_confirm_field] == reset_phrase:
                #Call the master reset function here
                messages.success(request, "Plom instance successfully wiped.")
                return redirect("home")
            form.add_error(_confirm_field, "Phrase is incorrect")
        context.update({"wipe_form": form})
        return render(request, "base/reset_confirm.html", context=context)
