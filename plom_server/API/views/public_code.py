# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2022-2025 Colin B. Macdonald
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2024 Bryan Tanady
# Copyright (C) 2025 Philip D. Loewen

from rest_framework.response import Response
from rest_framework.request import Request
from rest_framework.views import APIView
from rest_framework import status

from plom_server.Base.services import Settings

from .utils import _error_response


class PublicCodeAPIView(APIView):
    """Get/set the server's public code."""

    # GET /api/v0/public_code
    def get(self, request: Request) -> Response:
        """Get the current public code.

        Returns:
            The current public code as a string with status 200.
            If there is not yet a public code, return the empty string.
        """
        public_code = Settings.get_public_code()
        if not public_code:
            public_code = ""
        return Response(public_code)

    # POST /api/v0/public_code
    def post(self, request: Request) -> Response:
        """Manager users can set the current public code.

        Args:
            request: An HTTP request that includes `new_public_code` in
                its json payload.

        Returns:
            A 200 response object with no content on success.
            Status 400 if you don't provide the `new_public_code`.
            Status 403 indicates user is not in the "manager" group.
            Status 409 indicates that changing the public code is not allowed,
            which currently never happens but potentially could in the future.
            TODO: someone should be enforcing validity (6 digits etc?).
        """
        group_list = list(request.user.groups.values_list("name", flat=True))
        if "manager" not in group_list:
            return _error_response(
                'Only users in the "manager" group can change the public code',
                status.HTTP_403_FORBIDDEN,
            )

        new_public_code = request.data.get("new_public_code")
        if not new_public_code:
            return _error_response(
                "Must include the `new_public_code` key",
                status.HTTP_400_BAD_REQUEST,
            )

        Settings.set_public_code(new_public_code)

        return Response()
