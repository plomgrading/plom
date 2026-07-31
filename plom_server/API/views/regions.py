# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Colin B. Macdonald

from rest_framework.response import Response
from rest_framework.request import Request
from rest_framework.views import APIView
from rest_framework import status

from django.core.exceptions import ObjectDoesNotExist

# from plom.common.exceptions import PlomDependencyConflict
from plom_server.Preparation.services import QuestionRegionsService
from .utils import _error_response


class RegionsView(APIView):
    """Handle API requests to manipulate question regions."""

    # DELETE /api/beta/regions
    def delete(self, request: Request) -> Response:
        """Remove all or particular question / version crop regions.

        Args:
            request: An HTTP request.

        Returns:
            An empty response with status 204, on success.
            Status 403 if the caller is not in the 'manager' group;
            status 409 if TODO.
        """
        # Reject the request if the user is not in the 'manager' group.
        group_list = list(request.user.groups.values_list("name", flat=True))
        if "manager" not in group_list:
            return _error_response(
                'Only users in the "manager" group delete regions.',
                status.HTTP_403_FORBIDDEN,
            )

        # TODO: question_index input?
        QuestionRegionsService.reset_question_regions()
        return Response(status=status.HTTP_204_NO_CONTENT)

    # GET /api/beta/regions
    def get(self, request: Request) -> Response:
        """Get the current list of regions.

        Args:
            request: An HTTP request.

        Returns:
            A Response object containing the regions as a dict, with status 200,
            on success.
        """
        return Response(QuestionRegionsService.get_question_regions())

    # POST /api/beta/regions/{qidx}/{ver}/{page}
    def post(self, request: Request) -> Response:
        """Create a crop region for a particular question/ver/page.

        TODO: page?
        TODO: who should be allowed to set this?  Probably at least
        lead_markers if we want it from the client...  Consider saving
        the username into the region metadata to future-proof each user
        potentially saving their own.

        Args:
            request: An HTTP request.

        POST Data:
            TODO: TODO:

        Returns:
            An empty response with status code 204, on success. Status code 403
            if the user is not in the 'manager' group; status code 409 if the
            operation has been blocked by some kind of conflict.
        """
        # Reject the request if the user is not in the 'manager' group.
        group_list = list(request.user.groups.values_list("name", flat=True))
        if "manager" not in group_list:
            return _error_response(
                'Only users in the "manager" group can set regions.',
                status.HTTP_403_FORBIDDEN,
            )

        # # TODO: fail if not spce
        # if PaperInfoService.is_paper_database_populated():
        #     return _error_response(
        #         "PQV map is not empty. Consider deleting before re-generating.",
        #         status.HTTP_409_CONFLICT,
        #     )

        # ntp_default = StagingStudentService().get_minimum_number_to_produce()
        # ntp = request.POST.get("number_to_produce", ntp_default)
        # number_to_produce = int(ntp)

        # TODO: set stuff
        return _error_response(
            "POST regions not built yet!", status.HTTP_501_NOT_IMPLEMENTED
        )

        return Response(status=status.HTTP_204_NO_CONTENT)


class RegionsSubdivideView(APIView):
    """Handle API requests to subdivide a page into regions."""

    # POST /api/beta/regions/subdivide/{pagenum}
    def post(self, request: Request, *, pagenum: int) -> Response:
        """Create regions for questions that share a page.

        Args:
            request: An HTTP request.

        Keyword Args:
            pagenum: which page, indexed from one.

        POST Data:
            The post data should contain a list of "divisions", then length
            of which must be one less than the number of questions that
            share this page.

        Returns:
            An empty response with status code 204, on success. Status code 403
            if the user is not in the 'manager' group; status code 400 for
            malformed floats or wrong number of floats; status code 409 if the
            operation has been blocked by a conflict (no spec for example).
        """
        # Reject the request if the user is not in the 'manager' group.
        group_list = list(request.user.groups.values_list("name", flat=True))
        if "manager" not in group_list:
            return _error_response(
                'Only users in the "manager" group can set regions.',
                status.HTTP_403_FORBIDDEN,
            )

        div = request.data.get("divisions")
        try:
            div = [float(x) for x in div]
        except ValueError as e:
            return _error_response(e, status.HTTP_400_BAD_REQUEST)

        # TODO: support version-specific setting
        try:
            QuestionRegionsService.subdivide_page(pagenum, div)
        except ValueError as e:
            return _error_response(e, status.HTTP_400_BAD_REQUEST)
        except ObjectDoesNotExist:
            return _error_response("no spec", status.HTTP_409_CONFLICT)

        return Response(status=status.HTTP_204_NO_CONTENT)
