# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2022-2025 Colin B. Macdonald
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2024 Bryan Tanady
# Copyright (C) 2025 Philip D. Loewen

from django.core.exceptions import ObjectDoesNotExist
from rest_framework.response import Response
from rest_framework.request import Request
from rest_framework.views import APIView
from rest_framework import status

from plom.plom_exceptions import PlomDependencyConflict
from plom_server.Papers.services import SpecificationService
from plom_server.SpecCreator.services import SpecificationUploadService

from .utils import debugnote
from .utils import _error_response


class SpecificationHandler(APIView):
    """Handle transactions involving the Assessment Specification."""

    # GET /api/v0/spec (and, for backward compatibility, /info/spec)
    def get(self, request: Request) -> Response:
        """Get the current assessment spec.

        Returns:
            (200) JsonResponse: the current spec.
            (400) spec not found.
        """
        if not SpecificationService.is_there_a_spec():
            return _error_response(
                "Server does not have a spec.", status.HTTP_400_BAD_REQUEST
            )

        the_spec = SpecificationService.get_the_spec()
        the_spec.pop("privateSeed", None)

        return Response(the_spec)

    # POST /api/v0/spec
    def post(self, request: Request) -> Response:
        """Use a string containing TOML to replace the server's current spec, or to instantiate a brand new one.

        Args:
            request: An HTTP request in which the data dict has a string-type
                key named "spec_toml" whose corresponding value is a
                utf-8 string containing everything read from a well-formed
                spec file in TOML format.

        Returns:
            (200) JsonResponse: the freshly-installed new spec.
            (400) TOML didn't parse correctly.
            (403) User does not belong to "manager" group.
            (409) Changing the spec is not allowed. Typically because the server is in an advanced state.
            (500) Spec retrieval failed, even though spec updating seemed to succeed. Eek!
        """
        group_list = list(request.user.groups.values_list("name", flat=True))
        if "manager" not in group_list:
            return _error_response(
                'Only users in the "manager" group can upload an assessment spec',
                status.HTTP_403_FORBIDDEN,
            )

        spec_toml_string = request.data.get("spec_toml", "")
        if len(spec_toml_string) == 0:
            # debugnote("SpecificationHandler: String length 0 for spec_toml_string.")
            return _error_response(
                "Given TOML string has length 0. Assessment spec unchanged.",
                status.HTTP_400_BAD_REQUEST,
            )

        # debugnote("SpecificationHandler: Found nontrivial spec_toml_string.")
        try:
            SUS = SpecificationUploadService(toml_string=spec_toml_string)
        except ValueError as e:
            # debugnote("SpecificationHandler: Failed to instantiate SUS.")
            return _error_response(
                "Given TOML string was rejected. Assessment spec unchanged. "
                + f"Details: {e}",
                status.HTTP_400_BAD_REQUEST,
            )

        # debugnote("SpecificationHandler: spec_toml_string passes initial checks.")
        try:
            SpecificationService.remove_spec()
        except ObjectDoesNotExist:
            # No problem, maybe this is the first upload
            pass
        except PlomDependencyConflict as e:
            return _error_response(
                "Modifying the assessment spec is not allowed. Details:\n" + f"{e}",
                status.HTTP_409_CONFLICT,
            )

        # debugnote("SpecificationHandler: The server's spec slot is now vacant.")

        try:
            SUS.save_spec()  # Main activity is load_spec_from_dict, done elsewhere
        except ValueError as e:
            debugnote(f"SpecificationHandler: save_spec failed, with details {e}.")
            return _error_response(
                "SpecificationHandler: Failed to save spec.",
                status.HTTP_409_CONFLICT,
            )

        # TODO: we probably should not explicitly throw 500, revisit this
        # during/after https://gitlab.com/plom/plom/-/merge_requests/3182
        # along with changes to "SUS".
        if not SpecificationService.is_there_a_spec():
            return _error_response(
                "SpecificationHandler: Catastrophe beyond imagining.",
                status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        the_spec = SpecificationService.get_the_spec()
        the_spec.pop("privateSeed", None)

        return Response(the_spec)
