# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Colin B. Macdonald

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from Base.base_group_views import ScannerRequiredView


class TroublesAfootGenericErrorView(ScannerRequiredView):
    def get(self, request: HttpRequest, *, hint: str) -> HttpResponse:
        """Render an unexpected or semi-expected "error page" using kludges.

        We'd probably like to show a real error page, like 404 or 500.
        But for technical reasons we might not know how (yet!).
        Code calling this should be improved if possible.

        TODO: no particular reason this should live in Scan or be a
        ScannerRequiredView.

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
        context = self.build_context()
        context["hint"] = hint
        return render(request, "Scan/troubles_afoot.html", context)
