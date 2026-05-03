# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2022-2026 Colin B. Macdonald
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2023 Julian Lapenna
# Copyright (C) 2024 Bryan Tanady

import json
import pathlib

from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist
from rest_framework import status
from rest_framework.response import Response
from rest_framework.request import Request
from rest_framework.views import APIView

from plom.misc_utils import unpack_task_code
from plom.plom_exceptions import (
    PlomConflict,
    PlomTaskDeletedError,
    PlomTaskChangedError,
    PlomQuotaLimitExceeded,
)

from plom_server.Mark.services import QuestionMarkingService, MarkingTaskService
from plom_server.Mark.services import mark_task, page_data
from plom_server.Progress.services import UserInfoService
from plom_server.Papers.services import PaperInfoService
from .utils import _error_response


def _400(m):
    return _error_response(m, status.HTTP_400_BAD_REQUEST)


class MarkTaskNextAvailable(APIView):
    """Get the next currently-available marking task."""

    # GET: /MK/tasks/available
    def get(self, request: Request) -> Response:
        """Get the next currently-available marking task.

        Responds with a code for the next available marking task.
        Callers then need to "claim" that marking task if they want it.
        We are not holding it for you: the server may tell two users
        the same task is available.

        The behaviour is influenced by various options.  A confusing case is
        ``tag`` which is a *preference* and not a *requiremennt*.
        You can still receive tasks that do not match the tag.

        Returns:
            200: An available task exists, returns the task code as a string.
            204: There are no available tasks.
        """
        data = request.query_params

        def int_or_None(x):
            return None if x is None else int(x)

        try:
            question = int_or_None(data.get("q"))
            version = int_or_None(data.get("v"))
            min_paper_num = int_or_None(data.get("min_paper_num"))
            max_paper_num = int_or_None(data.get("max_paper_num"))
        except ValueError as e:
            return _error_response(e, status.HTTP_423_LOCKED)

        _tag: str | None = data.get("tags")
        if _tag:
            tags = _tag.split(",")
        else:
            tags = []

        task = QuestionMarkingService.get_first_available_task(
            question_idx=question,
            version=version,
            user=request.user,
            min_paper_num=min_paper_num,
            max_paper_num=max_paper_num,
            tags=tags,
        )

        if not task and tags:
            # didn't find anything tagged, so try again without
            task = QuestionMarkingService.get_first_available_task(
                question_idx=question,
                version=version,
                user=request.user,
                min_paper_num=min_paper_num,
                max_paper_num=max_paper_num,
            )

        if not task:
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(task.code, status=status.HTTP_200_OK)


class MarkTask(APIView):
    """Handles claiming or surrendering tasks, and submitting annotations."""

    # PATCH: /MK/tasks/{code}
    def patch(self, request: Request, *, code: str) -> Response:
        """Attach a user to a marking task and return the task's metadata.

        Reply with status 200, or 409 if someone else has claimed this
        task, or a 404 if there it not yet such a task (not scanned yet).
        If a version query parameter (e.g., "?version=2") was supplied,
        and it does not match the task, reply with a 417.  If you don't
        send version, we set it to None which means no such check will
        be made: you're claiming the task regardless of what version it is.
        400 for a poorly formatted request, such as invalid task code.
        If you're not in the "marker" group, you'll get a 403 error.
        """
        calling_user = request.user
        group_list = list(request.user.groups.values_list("name", flat=True))
        if "marker" not in group_list:
            return _error_response(
                f"You ({calling_user}) cannot claim marking tasks because"
                ' your account is not in the "marker" group',
                status.HTTP_403_FORBIDDEN,
            )

        data = request.query_params
        version = data.get("version", None)
        if version is not None:
            version = int(version)
        try:
            papernum, question_idx = unpack_task_code(code)
        except ValueError as e:
            return _error_response(e, status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            try:
                task = mark_task.get_latest_task(
                    papernum, question_idx, question_version=version
                )
            except ObjectDoesNotExist as e:
                return _error_response(e, status.HTTP_404_NOT_FOUND)
            except ValueError as e:
                return _error_response(e, status.HTTP_417_EXPECTATION_FAILED)

            try:
                MarkingTaskService.assign_task_to_user(task.pk, request.user)
            except RuntimeError as e:
                return _error_response(e, status.HTTP_409_CONFLICT)

            question_data = page_data.get_question_pages_list(papernum, question_idx)
            tags = MarkingTaskService().get_tags_for_task_pk(task.pk)
            return Response([question_data, tags, task.pk])

    # DELETE: /MK/tasks/{code}
    def delete(self, request: Request, *, code: str) -> Response:
        """Surrender (detach) a user from a marking task.

        Reply with status 200, or 400 if malformed task code.  409 if the
        task was taken by someone else, or didn't exist etc.
        """
        try:
            papernum, question_idx = unpack_task_code(code)
        except ValueError as e:
            return _error_response(e, status.HTTP_400_BAD_REQUEST)

        try:
            MarkingTaskService.surrender_task(request.user, papernum, question_idx)
        except ValueError as e:
            return _error_response(e, status.HTTP_404_NOT_FOUND)
        except PlomConflict as e:
            return _error_response(e, status.HTTP_409_CONFLICT)
        return Response()

    # POST: /MK/tasks/{code}
    def post(self, request: Request, *, code: str) -> Response:
        """Accept a marker's grade and annotation for a task.

        Args:
            request: should contain a file keyed by "annotation_image"
                and data of key-value pairs.  The data has keys "score",
                "marking_time", "md5sum", "integrity_check", "rubric",
                and "annotations".
                "rubric" can be repeated to give a list of integers
                (which will come as strings b/c I think http just does that),
                corresponding to the rids of the Rubrics used in this
                annotation.  It can be empty.  If you use a Rubric more than
                once, repeat it in the list.  Providing only the integer rids
                means Plom will assume you're using the latest revisions of each.
                To enable more precise checking, pass in ``<rid>.<rev>``,
                ``<rid>r<rev>``, or ``<rid>rev<rev>`` (for example "14.3"
                "15r0" or "15rev0").  That way you'll get errors if those are
                not the latest revisions.
                Optionally, you can provide "annotations" containing an ascii
                string encoding
                of JSON: in Python you can create this using
                ``json.dumps(annotation_data)``.  The expected format of
                the dictionary `annotation_data` is hopefully documented
                elsewhere.
                This format is still influx: expect changes in the future.

        Keyword Args:
            code: a string such as "0123g4" specifying a task.

        Returns:
            200: returns two integers, first the number of marked papers
            for this question/version and the total number of papers for
            this question/version.
            400: malformed input of some sort, such as poorly formed task code.
            404: currently not returned but perhaps in the past this was used
            instead of 410, in some cases (depending on a regex matching of
            task codes.  Its possible in the future the server might distinguish
            between "never existed" (404) and "gone away" (410), so clients should
            handle both to be future-proof.
            406: integrity fail: client submitted to out-of-date task.
            409: task has changed.
            410: task is non-existent, either never was, or has now gone away.
            403: you're not in the "marker" group.
        """
        calling_user = request.user
        group_list = list(request.user.groups.values_list("name", flat=True))
        if "marker" not in group_list:
            return _error_response(
                f"You ({calling_user}) cannot mark tasks because"
                ' your account is not in the "marker" group',
                status.HTTP_403_FORBIDDEN,
            )

        mts = MarkingTaskService()
        data = request.POST
        files = request.FILES

        try:
            score = float(data["score"])
        except KeyError as e:
            return _400(f"You must provide the value: {e}")
        except IndexError:
            return _400('Multiple values for "score", expected 1')
        except (ValueError, TypeError) as e:
            return _400(f'Could not cast "score" as float: {e}')

        try:
            marking_time = float(data["marking_time"])
        except KeyError as e:
            return _400(f"You must provide the value: {e}")
        except (ValueError, TypeError) as e:
            return _400(f'Could not cast "marking_time" as float: {e}')

        try:
            integrity_check = int(data["integrity_check"])
        except KeyError as e:
            return _400(f"You must provide the value: {e}")
        except (ValueError, TypeError) as e:
            return _400(f'Could not get "integrity_check" as a int: {e}')

        try:
            md5sum = str(data["md5sum"])
        except KeyError as e:
            return _400(f"You must provide the value: {e}")

        rubric_list = []
        for x in data.getlist("rubric"):
            print(x)
            if "." in x:
                rid, rev = x.split(".")
            elif "rev" in x:
                rid, rev = x.split("rev")
            elif "r" in x:
                rid, rev = x.split("r")
            else:
                rid, rev = x, None

            try:
                rid = int(rid)
            except (ValueError, TypeError) as e:
                return _400(f'failed to extract integer "rid" from rubric "{x}": {e}')
            if rev is not None:
                try:
                    rev = int(rev)
                except (ValueError, TypeError) as e:
                    return _400(
                        f'failed to extract integer "rev" from rubric "{x}": {e}'
                    )
            rubric_list.append((rid, rev))

        raw_annotation_data = data.get("annotations")
        if raw_annotation_data is None:
            raw_annotation_data = "{}"

        # TODO: error handling around this loads, unless we stop doing this
        annot_data = json.loads(raw_annotation_data)
        # TODO: temporarily do extra work here when client agent is org.plomgrading.PlomClient
        if False:
            # Colin thinks this is a very bad idea
            src_img_data = annot_data["base_images"]
            for image_data in src_img_data:
                # TODO: this looks like direct file access on the server, Issue #3888.
                img_path = pathlib.Path(image_data["server_path"])
                if not img_path.exists():
                    return _400("Invalid original-image in request")

            # take rid rev pairs from the annotation data
            # TODO: this is temporary/debugging
            from plom_server.Mark.services.annotations import (
                _extract_rubric_rid_rev_pairs,
            )

            rubric_list2 = _extract_rubric_rid_rev_pairs(annot_data)
            print(rubric_list2)
            # rubric_list = rubric_list2

        annotation_image = files["annotation_image"]

        try:
            # TODO: use query param, allow client to override require_latest_rubrics=True?
            QuestionMarkingService.mark_task(
                code,
                user=request.user,
                score=score,
                marking_time=marking_time,
                integrity_check=integrity_check,
                annotation_data=annot_data,
                annotation_image=annotation_image,
                annotation_image_md5sum=md5sum,
                rubric_list=rubric_list,
            )
        except ValueError as e:
            return _error_response(e, status.HTTP_400_BAD_REQUEST)
        except KeyError as e:
            # TODO: unclear where KeyError can happen, perhaps delete this case?
            return _error_response(e, status.HTTP_400_BAD_REQUEST)
        except PlomTaskChangedError as e:
            return _error_response(e, status.HTTP_409_CONFLICT)
        except PlomTaskDeletedError as e:
            return _error_response(e, status.HTTP_410_GONE)
        except PlomConflict as e:
            return _error_response(e, status.HTTP_406_NOT_ACCEPTABLE)
        except PlomQuotaLimitExceeded as e:
            return _error_response(e, status.HTTP_423_LOCKED)

        def int_or_None(x):
            return None if x is None else int(x)

        papernum, qidx = unpack_task_code(code)
        version = PaperInfoService.get_version_from_paper_question(papernum, qidx)

        username = request.user.username
        progress = UserInfoService.get_user_progress(username=username)
        n, m = mts.get_marking_progress(qidx, version)
        progress["total_tasks_marked"] = n
        progress["total_tasks"] = m
        return Response(progress, status=status.HTTP_200_OK)
