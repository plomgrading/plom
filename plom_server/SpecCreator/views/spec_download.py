# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024-2025 Colin B. Macdonald

import io

from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpRequest, HttpResponse, FileResponse, Http404

from plom_server.Base.base_group_views import ManagerRequiredView
from plom_server.Papers.services import SpecificationService


class SpecDownloadView(ManagerRequiredView):
    """Grab the toml of the current server specification."""

    def get(self, request: HttpRequest) -> HttpResponse | FileResponse:
        try:
            toml = SpecificationService.get_the_spec_as_toml()
        except ObjectDoesNotExist as e:
            raise Http404(e) from e
        return FileResponse(
            io.BytesIO(toml.encode("utf-8")),
            as_attachment=True,
            filename=SpecificationService.get_short_name_slug() + "_spec.toml",
        )
