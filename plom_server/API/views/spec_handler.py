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
from .utils import _error_response


class SpecificationHandler(APIView):
    """Handle transactions involving the Assessment Specification."""

    def get(self) -> Response:
        """Get the current spec.

        Returns:
            (200) JsonResponse: the current spec.
            (404) spec not found.
        """
        if not SpecificationService.is_there_a_spec():
            return _error_response(
                "Server does not have a spec", status.HTTP_400_BAD_REQUEST
            )

        the_spec = SpecificationService.get_the_spec()
        the_spec.pop("privateSeed", None)

        return Response(the_spec)

    def post(self, request: Request) -> Response:
        """Use a string containing TOML to replace the current spec, if any.

        Returns:
            (200) JsonResponse: the freshly-installed new spec.
            (400) Could not save the given spec.
            (404) Something went wrong.
        """
        SUS = SpecificationUploadService()

        if SpecificationService.is_there_a_spec():
            try:
                SUS.delete_spec()
            except Exception as e:
                return _error_response(
                    f"\nDeleting old spec failed, with exception {e}. Quitting!\n",
                    status.HTTP_HTTP_400_BAD_REQUEST,
                )

        # In principle this block should be redundant.
        if SpecificationService.is_there_a_spec():
            return _error_response(
                "\nDeleting old spec failed. Quitting!\n",
                status.HTTP_HTTP_400_BAD_REQUEST,
            )

        # There is no spec. Upload the given one.
        spec_toml_string = request.data["spec_toml"]  # Get the TOML string
        SUS.__init__(toml_string=spec_toml_string)  # Read it into the service
        try:
            SUS.save_spec()  # Main activity is load_spec_from_dict
        except Exception:
            return _error_response(
                "\nGiven spec would not save. Consider pre-validating it.\n",
                status.HTTP_400_BAD_REQUEST,
            )

        # Check again that everything is in order
        if not SpecificationService.is_there_a_spec():
            return _error_response(
                "Upload failed. No idea why.", status.HTTP_404_NOT_FOUND
            )

        the_spec = SpecificationService.get_the_spec()
        the_spec.pop("privateSeed", None)

        return Response(the_spec)
