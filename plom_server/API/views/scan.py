# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Colin B. Macdonald
# Copyright (C) 2025-2026 Aidan Murphy
# Copyright (C) 2025 Philip D. Loewen

from django.core.exceptions import ObjectDoesNotExist
from django.forms import ValidationError
from rest_framework.views import APIView
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework import status

from plom.plom_exceptions import (
    PlomConflict,
    PlomPushCollisionException,
    PlomBundleLockedException,
)

from plom_server.Papers.models import MobilePage
from plom_server.Papers.services import SpecificationService
from plom_server.Scan.services import ScanService, ManageScanService
from .utils import _error_response


class ScanListBundles(APIView):
    """API related to bundles."""

    # GET: /api/beta/scan/bundles
    def get(self, request: Request) -> Response:
        """API to list all bundles."""
        bundle_status = ScanService().staging_bundle_status()
        return Response(bundle_status, status=status.HTTP_200_OK)

    # POST: /api/beta/scan/bundles
    def post(self, request: Request) -> Response:
        """API to upload a new bundle.

        On success (200) you'll get a dictionary with the key
        ``"bundle_id"`` giving the id of the newly-created bundle.

        Only users in the "scanner" group can upload new bundles,
        others will receive a 403.

        The bundle filename cannot begin with an underscore, that
        will result in a 400.

        The bundle must have a distinct sha256 hash from existing
        bundles, or you'll get a 409.  Passing the "force" query
        parameter makes this a warning rather than an error.
        """
        user = request.user
        group_list = list(request.user.groups.values_list("name", flat=True))
        if "scanner" not in group_list:
            return _error_response(
                'Only users in the "scanner" group can upload files',
                status.HTTP_403_FORBIDDEN,
            )
        pdf = request.FILES.get("pdf_file")

        # TODO: consider exposing force_render and read_after via query params
        if "force" in request.query_params:
            force = True
        else:
            force = False

        try:
            info_dict = ScanService.upload_bundle(
                pdf, user, read_after=True, force=force
            )
        except ValidationError as e:
            return _error_response(e, status.HTTP_400_BAD_REQUEST)
        except PlomConflict as e:
            return _error_response(e, status.HTTP_409_CONFLICT)

        return Response(info_dict, status=status.HTTP_200_OK)


class ScanBundleActions(APIView):
    """API related to bundles."""

    # PATCH: /api/beta/scan/bundle/{bundle_id}
    def patch(self, request: Request, *, bundle_id: int) -> Response:
        """API to push a bundle.

        On success (200), the return will be TODO: still a WIP.

        Only "scanner" users including managers can do this; others will
        get a 403.
        """
        group_list = list(request.user.groups.values_list("name", flat=True))
        if "scanner" not in group_list:
            return _error_response(
                'Only users in the "scanner" group can push bundles',
                status.HTTP_403_FORBIDDEN,
            )

        try:
            ScanService.push_bundle_to_server(bundle_id, request.user)
        except ObjectDoesNotExist as e:
            return _error_response(e, status.HTTP_404_NOT_FOUND)
        except ValueError as err:
            return _error_response(err, status=status.HTTP_400_BAD_REQUEST)
        except PlomPushCollisionException as err:
            return _error_response(err, status=status.HTTP_409_CONFLICT)
        except PlomBundleLockedException as err:
            return _error_response(err, status=status.HTTP_406_NOT_ACCEPTABLE)
        except RuntimeError as err:
            return _error_response(
                f"Unexpected error: {err}", status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return Response({"bundle_id": bundle_id}, status=status.HTTP_200_OK)

    # DELETE: /api/beta/scan/bundle/{bundle_id}
    def delete(self, request: Request, *, bundle_id: int) -> Response:
        """API to delete a bundle.

        On success (200), the return will be the id of the bundle deleted

        Only "scanner" users including managers can do this; others will
        get a 403.

        Deletion will fail if the bundle is 'locked' (being processed or
        already pushed) and a 406 will be returned.
        """
        group_list = list(request.user.groups.values_list("name", flat=True))
        if "scanner" not in group_list:
            return _error_response(
                'Only users in the "scanner" group can delete bundles',
                status.HTTP_403_FORBIDDEN,
            )
        try:
            ScanService().remove_bundle_by_pk(bundle_id)
        except ObjectDoesNotExist:
            return _error_response(
                f"No bundle id {bundle_id}",
                status.HTTP_404_NOT_FOUND,
            )
        except PlomBundleLockedException as err:
            return _error_response(err, status=status.HTTP_406_NOT_ACCEPTABLE)

        return Response({"bundle_id": bundle_id}, status=status.HTTP_200_OK)


class ScanMapBundle(APIView):
    """API related to mapping a bundle."""

    # POST: /api/beta/scan/bundle/{bundle_id}/{page}/map
    def post(self, request: Request, *, bundle_id: int, page: int) -> Response:
        """API to map one page of a Staging Bundle onto questions.

        Args:
            request: A Request object with some important clues in the
                query parameters: `papernum` indicates to which paper to
                assign the page.  `qidx` indicates a question index and
                maybe be repeated.  `page_dest` specifies a string, "all",
                "dnm" or "discard".  If you pass `page_dest`, you should
                *not* pass `qidx` as well.

        Keyword Args:
            bundle_id: the integer that uniquely identifies which bundle to work on.
            page: the integer position of the page to work on in that bundle.
                The first page in the bundle has number 1 (not 0).

        Returns:
            A Response object. On success, the content is empty and the status is 204.
            Status 403 is returned if the calling user is outside the "scanner" group;
            status 400 indicates an error of some kind in the input parameters.
        """
        group_list = list(request.user.groups.values_list("name", flat=True))
        if "scanner" not in group_list:
            return _error_response(
                'Only users in the "scanner" group can map pages via the API',
                status.HTTP_403_FORBIDDEN,
            )
        data = request.query_params

        page_dest = data.get("page_dest")  # Expect one of "all", "dnm", "discard"
        question_idx_list = data.getlist("qidx")
        papernum = data.get("papernum")

        if page_dest is not None and question_idx_list:
            return _error_response(
                f'Do not specify both a keyword "{page_dest}" and'
                f' qidx "{question_idx_list}" in the same call',
                status.HTTP_400_BAD_REQUEST,
            )

        if page_dest == "discard":
            try:
                ScanService.discard_staging_bundle_page(
                    bundle_id, page, user=request.user
                )
            except ValueError as e:
                return _error_response(e, status.HTTP_400_BAD_REQUEST)
            except ObjectDoesNotExist as e:
                return _error_response(
                    f"Probably no bundle id {bundle_id} or page {page}: {e}",
                    status.HTTP_404_NOT_FOUND,
                )
            return Response(status=status.HTTP_204_NO_CONTENT)

        if page_dest is None:
            try:
                question_idx_list = [int(n) for n in question_idx_list]
            except ValueError as e:
                return _error_response(
                    f"ScanMapBundle got a non-integer qidx: {e}",
                    status.HTTP_400_BAD_REQUEST,
                )
        elif page_dest == "all":
            question_idx_list = [
                1 + j for j in range(SpecificationService.get_n_questions())
            ]
        elif page_dest == "dnm":
            question_idx_list = [MobilePage.DNM_qidx]
        else:
            return _error_response(
                f"Cannot construct list of questions from {data}",
                status.HTTP_400_BAD_REQUEST,
            )

        try:
            ScanService.map_bundle_page(
                bundle_id,
                page,
                user=request.user,
                papernum=papernum,
                question_indices=question_idx_list,
            )
        except (ValueError, PlomConflict) as e:
            return _error_response(e, status.HTTP_400_BAD_REQUEST)
        except ObjectDoesNotExist as e:
            return _error_response(
                f"Probably no bundle id {bundle_id} or page {page}: {e}",
                status.HTTP_404_NOT_FOUND,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)


class ScanListPapers(APIView):
    """API related to papers."""

    # GET: /api/beta/scan/papers
    def get(self, request: Request) -> Response:
        """API request for scanning status of papers."""
        unused_papers_list = ManageScanService.get_all_unused_papers()

        complete_papers_list = ManageScanService.get_all_complete_papers()
        incomplete_papers_list = ManageScanService.get_all_incomplete_papers()

        papers_catalogue = {
            "unused": unused_papers_list,
            "complete": complete_papers_list,
            "incomplete": incomplete_papers_list,
        }

        return Response(papers_catalogue, status=status.HTTP_200_OK)
