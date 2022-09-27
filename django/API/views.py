# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2022 Brennen Chiu

from django.http import JsonResponse, HttpResponseBadRequest
from django.views import View

from Papers.services import SpecificationService


class InfoSpec(View):
    """
    Return the public part of the specification.

    Returns:
        (200) JsonResponse: the spec
        (400) spec not found
    """

    def get(self, request):
        spec = SpecificationService()
        if not spec.is_there_a_spec():
            return HttpResponseBadRequest("Server does not yet have a spec.\n")

        the_spec = spec.get_the_spec()
        the_spec.pop('privateSeed', None)
        the_spec.pop('publicCode', None)

        return JsonResponse(the_spec)
