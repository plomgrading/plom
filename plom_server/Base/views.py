# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024-2025 Colin B. Macdonald
# Copyright (C) 2024 Aden Chan
# Copyright (C) 2024 Andrew Rechnitzer

import importlib

from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render, redirect
from django.urls import reverse
from django.contrib import messages
from django.views.generic import View
from django_huey import get_queue

from .base_group_views import ManagerRequiredView
from .forms import CompleteWipeForm
from .services import big_red_button

from Papers.services import SpecificationService
from Scan.services import ScanService

from plom.plom_exceptions import PlomDependencyConflict, PlomDatabaseCreationError


class TroublesAfootGenericErrorView(View):
    """View class for some kludgey error handling, hopefully not used much."""

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


class ServerStatusView(ManagerRequiredView):
    """View class for displaying server status."""

    def get(self, request: HttpRequest) -> HttpResponse:
        """Handles the GET request for the server status.

        Args:
            request (HttpRequest): The HTTP request object.

        Returns:
            An HTTP response object.
        """
        # importing at the top seems wasteful
        from huey import __version__ as huey_version
        from django import __version__ as django_version
        from pymupdf import __version__ as pymupdf_version

        context = self.build_context()
        # TODO: need a service?
        queue = get_queue("tasks")

        context.update(
            {
                "django_version": django_version,
                "huey_version": huey_version,
                "pymupdf_version": pymupdf_version,
                "zxingcpp_version": importlib.metadata.version("zxing-cpp"),
                "queue_length": len(queue),
            }
        )
        return render(request, "base/server_status.html", context)


class ResetView(ManagerRequiredView):
    """View class for handling the reset functionality."""

    def get(self, request: HttpRequest) -> HttpResponse:
        """Handles the GET request for the reset functionality.

        Args:
            request (HttpRequest): The HTTP request object.

        Returns:
            An HTTP response object.
        """
        context = self.build_context()
        context.update({"bundles_staged": ScanService().staging_bundles_exist()})
        return render(request, "base/reset.html", context)


class ResetConfirmView(ManagerRequiredView):
    """View class for confirming the reset of a Plom instance."""

    def get(self, request: HttpRequest) -> HttpResponse:
        """Handles the GET request for the reset confirmation view.

        Args:
            request (HttpRequest): The HTTP request object.

        Returns:
            HttpResponse: The HTTP response object.
        """
        context = self.build_context()
        form = CompleteWipeForm()
        try:
            reset_phrase = SpecificationService.get_shortname()
        except ObjectDoesNotExist:
            context.update({"no_spec": True})
            return render(request, "base/reset_confirm.html", context=context)
        context.update(
            {
                "no_spec": False,
                "bundles_staged": ScanService().staging_bundles_exist(),
                "wipe_form": form,
                "reset_phrase": reset_phrase,
            }
        )
        return render(request, "base/reset_confirm.html", context=context)

    def post(self, request: HttpRequest) -> HttpResponse:
        """Handles the POST request for the reset confirmation view.

        Args:
            request: The HTTP request object.

        Returns:
            A HTTP response object.
        """
        context = self.build_context()
        form = CompleteWipeForm(request.POST)
        # TODO: one might expect the validator should checks if this matches
        reset_phrase = SpecificationService.get_shortname()
        _confirm_field = "confirmation_field"
        if not form.is_valid():
            # not sure this can happen, or what to do if it does; for now
            # display poorly formatted error message on the home screen
            messages.error(request, f"Something expected happened: {form}")
            return redirect("home")
        if form.cleaned_data[_confirm_field] == reset_phrase:
            try:
                big_red_button.reset_assessment_preparation_database()
            except (PlomDependencyConflict, PlomDatabaseCreationError) as err:
                messages.add_message(request, messages.ERROR, f"{err}")
                return redirect(reverse("prep_conflict"))

            messages.success(request, "Plom instance successfully wiped.")
            return redirect("home")
        else:
            form.add_error(_confirm_field, "Phrase is incorrect")
            context.update(
                {
                    "bundles_staged": ScanService().staging_bundles_exist(),
                    "wipe_form": form,
                }
            )
            return render(request, "base/reset_confirm.html", context=context)
