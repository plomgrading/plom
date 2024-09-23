# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2022-2023 Brennen Chiu
# Copyright (C) 2023 Natalie Balashov
# Copyright (C) 2023-2024 Andrew Rechnitzer
# Copyright (C) 2024 Colin B. Macdonald

from django.http import HttpResponse
from django_htmx.http import HttpResponseClientRefresh, HttpResponseClientRedirect
from django.urls import reverse
from django.contrib import messages

from Base.base_group_views import ScannerRequiredView

from ..services import ScanService
from plom.plom_exceptions import PlomBundleLockedException, PlomPushCollisionException


class PushAllPageImages(ScannerRequiredView):
    """Push all page-images that pass the QR validation checks.

    Note that this is called by a htmx-post request.
    """

    def post(self, request: HttpResponse, *, bundle_id: int) -> HttpResponse:
        try:
            ScanService().push_bundle_to_server(bundle_id, request.user)
        except ValueError as err:
            messages.add_message(request, messages.ERROR, f"{err}")
            return HttpResponseClientRedirect(
                reverse("scan_bundle_lock", args=[bundle_id])
            )
        except PlomBundleLockedException as err:
            messages.add_message(request, messages.ERROR, f"{err}")
            # Note: reverse gives a view; that view should consume messages
            return HttpResponseClientRedirect(
                reverse("scan_bundle_lock", args=[bundle_id])
            )
        except PlomPushCollisionException as err:
            messages.add_message(request, messages.ERROR, f"{err}")
            # Note: reverse gives a view; that view should consume messages
            return HttpResponseClientRedirect(
                reverse("scan_bundle_push_collision", args=[bundle_id])
            )
        except RuntimeError as err:
            messages.add_message(request, messages.ERROR, f"{err}")
            # Note: reverse gives a view; that view should consume messages
            return HttpResponseClientRedirect(
                reverse("scan_bundle_push_error", args=[bundle_id])
            )

        return HttpResponseClientRefresh()
