# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024-2025 Colin B. Macdonald
# Copyright (C) 2024 Aden Chan
# Copyright (C) 2024 Andrew Rechnitzer

import importlib.metadata

from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.urls import reverse
from django.views.generic import View
from django_htmx.http import HttpResponseClientRedirect
from django_huey import get_queue

from plom.plom_exceptions import PlomDependencyConflict, PlomDatabaseCreationError
from plom_server.Papers.services import SpecificationService
from plom_server.Scan.services import ScanService

from .base_group_views import ManagerRequiredView
from .services import big_red_button


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
        from django import __version__ as django_version
        from pymupdf import __version__ as pymupdf_version

        context = self.build_context()
        # TODO: need a service?
        queues = []
        for queue_name in ("chores", "parentchores"):
            # TODO: fails with KeyError if no such queue...
            queue = get_queue(queue_name)
            # state = "ok?"
            # print("= = " * 80)
            # print(queue_name)
            # print(queue)
            # print(queue.storage.enqueued_items())
            # print(type(queue.storage.enqueued_items()))
            # print(queue.result_store_size())
            pending3 = queue.pending(limit=3)
            # TODO: is a list of of things like
            # <class 'plom_server.Finish.services.reassemble_service.huey_reassemble_paper'>
            # <ckass 'plom_server.Papers.services.paper_creator.huey_populate_whole_db'>
            info = {
                "name": queue_name,
                "queue": queue,
                "length": len(queue),
                "result_count": queue.result_count(),
                "other_info": queue.storage_kwargs,
                "pending3": pending3,
            }
            queues.append(info)

        server_url = f"{request.scheme}://{request.get_host()}"

        context.update(
            {
                "server_url": server_url,
                "django_version": django_version,
                "huey_version": importlib.metadata.version("huey"),
                "pymupdf_version": pymupdf_version,
                "zxingcpp_version": importlib.metadata.version("zxing-cpp"),
                "queues": queues,
            }
        )
        return render(request, "base/server_status.html", context)


class ResetView(ManagerRequiredView):
    """View class for confirming the reset of a Plom instance."""

    def get(self, request: HttpRequest) -> HttpResponse:
        """Handles the GET request for the reset confirmation view."""
        context = self.build_context()
        try:
            reset_phrase = SpecificationService.get_shortname()
            have_spec = True
        except ObjectDoesNotExist:
            reset_phrase = "yes"
            have_spec = False
        have_bundles_staged = ScanService().staging_bundles_exist()
        context.update(
            {
                "have_spec": have_spec,
                "bundles_staged": have_bundles_staged,
                "reset_phrase": reset_phrase,
            }
        )
        return render(request, "base/reset.html", context=context)

    def post(self, request: HttpRequest) -> HttpResponse:
        """Handles the POST request for the reset confirmation view.

        If the "reset_phrase_box" doesn't match, return a 400.  On success
        redirect to home.  Some other errors (unexpected ones) will go
        to a "preparation conflict" page.

        Called by htmx.
        """
        try:
            reset_phrase = SpecificationService.get_shortname()
        except ObjectDoesNotExist:
            reset_phrase = "yes"
        got_phrase = request.POST.get("reset_phrase_box")
        if got_phrase != reset_phrase:
            return HttpResponse(
                f'<b>Error:</b> phrase "{got_phrase}" does not match "{reset_phrase}"',
                status=400,
            )

        try:
            big_red_button.reset_assessment_preparation_database()
        except (PlomDependencyConflict, PlomDatabaseCreationError) as err:
            return HttpResponse(f"<b>Error:</b> {err}", status=400)

        messages.success(request, "Plom instance successfully wiped.")
        return HttpResponseClientRedirect(reverse("home"))
