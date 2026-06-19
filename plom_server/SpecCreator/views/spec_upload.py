# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024-2025 Colin B. Macdonald
# Copyright (C) 2026 Aidan Murphy

from json import JSONDecodeError

from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.urls import reverse

from django_htmx.http import HttpResponseClientRedirect

from plom.common.exceptions import PlomDependencyConflict

from plom_server.Base.base_group_views import ManagerRequiredView
from plom_server.Papers.services import SpecificationService

from rest_framework import serializers


class SpecUploadView(ManagerRequiredView):
    """Serves an "upload file" page but somewhat strangely doesn't process the form.

    Processing is handled by :class:`SpecEditorView`.
    """

    def get(self, request: HttpRequest) -> HttpResponse:
        context = self.build_context()
        context.update({"is_there_a_spec": SpecificationService.is_there_a_spec()})
        return render(request, "SpecCreator/spec_upload.html", context)


class SpecJsonUploadHTMXView(ManagerRequiredView):
    """Accepts a spec upload via a json string."""

    def post(self, request: HttpRequest) -> HttpResponse:
        spec = request.POST["spec"]
        try:
            SpecificationService.install_spec_from_json_string(spec)
        except PlomDependencyConflict as e:
            return HttpResponse(e, status=409)
        except PermissionDenied as e:
            return HttpResponse(e, status=403)
        except (JSONDecodeError, ValueError) as e:
            return HttpResponse(e, status=400)
        except RuntimeError as e:
            return HttpResponse(e, status=500)
        except serializers.ValidationError as e:
            error_list = SpecificationService._flatten_serializer_errors(e)
            pprint_error_list = [f"<li>{err_item}</li>" for err_item in error_list]
            pprint_error_list = "".join(pprint_error_list)
            error_msg = f"<ul>{pprint_error_list}</ul>"
            return HttpResponse(error_msg, status=400)

        return HttpResponseClientRedirect(reverse("spec_summary"))
