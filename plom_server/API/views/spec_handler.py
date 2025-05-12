# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2022-2025 Colin B. Macdonald
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2024 Bryan Tanady
# Copyright (C) 2025 Philip D. Loewen

import json
from rest_framework.response import Response
from rest_framework.request import Request
from rest_framework.views import APIView
from rest_framework import serializers
from rest_framework import status

from plom.plom_exceptions import PlomDependencyConflict
from plom_server.Papers.services import SpecificationService

from .utils import _error_response


class SpecificationHandler(APIView):
    """Handle transactions involving the Assessment Specification."""

    # GET /api/v0/spec
    def get(self, request: Request) -> Response:
        """Get the current assessment spec.

        Returns:
            The current spec, as a string in the Response's json,
            with status 200 on success. Status 400 indicates "spec not found."
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
        """Replace the server's current spec, or instantiate a brand new one.

        Args:
            request: An HTTP request that includes a serialized file
                accessible through key "spec_toml" and a boolean with
                key "force_public_code".

        Returns:
            A Response object whose json field contains the freshly-installed spec,
            with status 200, when everything works. Status 400 means TOML didn't
            parse correctly; status 403 indicates user is not in the "manager" group.
            Status 409 indicates that changing the spec is not allowed,
            typically because the server is in an advanced state.
        """
        group_list = list(request.user.groups.values_list("name", flat=True))
        if "manager" not in group_list:
            return _error_response(
                'Only users in the "manager" group can upload an assessment spec',
                status.HTTP_403_FORBIDDEN,
            )

        try:
            incoming = request.FILES["spec_toml"]
            spec_toml_string = incoming.read().decode("utf-8")
        except UnicodeDecodeError:
            return _error_response(
                "Unicode error makes progress impossible. Assessment spec unchanged.",
                status.HTTP_400_BAD_REQUEST,
            )

        # Note to self: Mixing json with a file upload imposes a special structure
        # on the incoming request object. It's easy to lose the json component.
        # Keeping it seems to require the explicit-serialization approach used here.

        # TODO: could instead use a query_param in the URL?
        data = json.loads(request.data["json_data"])
        force_public_code = data.get("force_public_code", False)

        # would be handled by next block but with a more verbose errors
        if not spec_toml_string:
            return _error_response(
                "Given TOML string empty or missing. Assessment spec unchanged.",
                status.HTTP_400_BAD_REQUEST,
            )

        try:
            SpecificationService.install_spec_from_toml_string(
                spec_toml_string,
                force_public_code=force_public_code,
            )
        except PlomDependencyConflict as e:
            return _error_response(e, status.HTTP_409_CONFLICT)
        except (SpecificationService.TOMLDecodeError, ValueError) as e:
            return _error_response(
                f"Cannot modify specification - {e}",
                status.HTTP_400_BAD_REQUEST,
            )
        except serializers.ValidationError as e:
            error_list = SpecificationService._flatten_serializer_errors(e)
            return _error_response(
                f"Cannot modify specification - {error_list}",
                status.HTTP_400_BAD_REQUEST,
            )
        except RuntimeError as e:
            return _error_response(
                f"Cannot modify, unexpected RuntimeError - {e}",
                status.HTTP_400_BAD_REQUEST,
            )

        the_spec = SpecificationService.get_the_spec()
        the_spec.pop("privateSeed", None)
        return Response(the_spec)
