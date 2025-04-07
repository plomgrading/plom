# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2022-2025 Colin B. Macdonald
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2024 Bryan Tanady
# Copyright (C) 2025 Philip D. Loewen

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.request import Request
from rest_framework import status

from plom_server.Papers.services import SpecificationService
from plom_server.SpecCreator.services import SpecificationUploadService
from plom_server.Preparation.services.preparation_dependency_service import (
    assert_can_modify_spec,
)
from .utils import _error_response

from plom.plom_exceptions import (
    PlomDependencyConflict,
)
from django.core.exceptions import ObjectDoesNotExist


import sys  # PDL wants this for debugging
import datetime


def debugnote(text: str):
    prefix = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:22]
    print(prefix + ": " + text)
    sys.stdout.flush()
    sys.stderr.flush()


class SpecificationHandler(APIView):
    """Handle transactions involving the Assessment Specification."""

    # PATCH /api/beta/spec
    def patch(self, request: Request) -> Response:
        """Testing code for HTTP PATCH method: this is just *always* an error."""
        prefix = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:22]
        return _error_response(
            prefix + ": We don't do PATCH here.", status.HTTP_400_BAD_REQUEST
        )

    # GET /api/beta/spec (and, for backward compatibility, /info/spec)
    def get(self, request: Request) -> Response:
        """Get the current spec.

        Returns:
            (200) JsonResponse: the current spec.
            (400) spec not found.
        """
        if not SpecificationService.is_there_a_spec():
            return _error_response(
                "Server does not have a spec", status.HTTP_400_BAD_REQUEST
            )

        the_spec = SpecificationService.get_the_spec()
        the_spec.pop("privateSeed", None)

        return Response(the_spec)

    # POST /api/beta/spec
    def post(self, request: Request) -> Response:
        """Use a string containing TOML to replace the current spec, if any.

        Returns:
            (200) JsonResponse: the freshly-installed new spec.
            (400) TOML didn't parse correctly.
            (403) Modifications forbidden.
            (500) This never happens.
        """
        debugnote("SpecificationHandler: Starting POST handling.")
        spec_toml_string = request.data.get("spec_toml", "")  # Get the TOML string
        if len(spec_toml_string) == 0:
            debugnote("SpecificationHandler: String length 0 for spec_toml_string.")
            return _error_response(
                "\nGiven TOML string has length 0. Assessment spec unchanged.\n"
                + f"Details: {e}\n",
                status.HTTP_400_BAD_REQUEST,
            )

        debugnote("SpecificationHandler: Found nontrivial spec_toml_string.")
        try:
            SUS = SpecificationUploadService(toml_string=spec_toml_string)
        except ValueError as e:
            debugnote("SpecificationHandler: Failed to instantiate SUS.")
            # return Response({"badnews":"Bad TOML! Return code should be 400"}) # TODO - Remove this hack
            # debugnote("SpecificationHandler: Should have returned, not printed this!")
            prefix = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:22]
            return _error_response(
                "\n"
                + prefix
                + ": Given TOML string was rejected. Consider pre-validating it.\n"
                + f"Details: {e}\n",
                status.HTTP_400_BAD_REQUEST,
            )

        try:
            SpecificationService.remove_spec()
        except ObjectDoesNotExist:
            # No problem, maybe this is the first upload
            pass
        except PlomDependencyConflict as e:
            prefix = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:22]
            return _error_response(
                "\n"
                + prefix
                + ": Modifying the assessment spec is not allowed. Details:\n"
                + f"{e}\n",
                status.HTTP_403_FORBIDDEN,
            )

        debugnote("SpecificationHandler: Opened vacancy for a spec.")

        # We're permitted to modify the spec, and there is a vacancy. Upload the given one.
        spec_toml_string = request.data["spec_toml"]  # Get the TOML string
        try:
            debugnote("SpecificationHandler: Start of try block.")
            SUS.save_spec()  # Main activity is load_spec_from_dict
            debugnote("SpecificationHandler: End of try block.")
        except Exception as e:
            prefix = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:22]
            debugnote(
                prefix
                + ": "
                + f"SpecificationHandler: Unknown exception with details {e}."
            )
            return _error_response(
                prefix
                + ": "
                + "\nGiven TOML string was rejected. Consider pre-validating it.\n"
                + f"Details: {e}\n",
                status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        debugnote("SpecificationHandler: Block of SUS actions has finished.")

        # Check again that everything is in order
        if not SpecificationService.is_there_a_spec():
            prefix = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:22]
            return _error_response(
                prefix + ": " + "Unforeseen catastrophe in SpecificationHandler.",
                status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        debugnote("SpecificationHandler: Final spec retrieval and exit.")
        # TODO: Review previous spec-upload functions to see what they return, and copy that

        the_spec = SpecificationService.get_the_spec()
        the_spec.pop("privateSeed", None)

        return Response(the_spec)
