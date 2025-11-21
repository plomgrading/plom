# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2022-2023 Brennen Chiu
# Copyright (C) 2023 Natalie Balashov
# Copyright (C) 2023-2024 Andrew Rechnitzer
# Copyright (C) 2024-2025 Colin B. Macdonald

from django.http import HttpResponse
from django_htmx.http import HttpResponseClientRefresh

from plom.plom_exceptions import PlomBundleLockedException, PlomPushCollisionException
from plom_server.Base.base_group_views import ScannerRequiredView
from ..services import ScanService


class PushAllPageImages(ScannerRequiredView):
    """Push all page-images that pass the QR validation checks.

    Note that this is called by a htmx-post request.
    """

    def post(self, request: HttpResponse, *, bundle_id: int) -> HttpResponse:
        try:
            ScanService().push_bundle_to_server(bundle_id, request.user)
        except (ValueError, PlomBundleLockedException) as err:
            return HttpResponse(err, status=409)
        except PlomPushCollisionException as err:
            return HttpResponse(
                f"Collision error: {err}: view the bundle for more information",
                status=409,
            )
        except RuntimeError as err:
            return HttpResponse(err, status=409)
        except Exception as err:
            # TODO: we don't like generic exception handlers but we got bit by
            # Issue #3926 so now catch all the unexpected errors too.
            msg = "Unexpected error, probably a bug.  "
            msg += "Please document what happened and "
            msg += "report it to the developers.<br> "
            msg += f"{err.__class__.__name__}: {err}"
            return HttpResponse(msg, status=400)

        return HttpResponseClientRefresh()
