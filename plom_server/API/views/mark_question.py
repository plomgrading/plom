# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2022-2024 Colin B. Macdonald
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2023 Julian Lapenna
# Copyright (C) 2024 Bryan Tanady


from __future__ import annotations

from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from plom.plom_exceptions import (
    PlomConflict,
    PlomTaskDeletedError,
    PlomTaskChangedError,
    PlomQuotaLimitExceeded,
)

from Mark.services import QuestionMarkingService, MarkingTaskService
from Mark.services import mark_task, page_data
from Progress.services import UserInfoServices
from .utils import _error_response


class QuestionMarkingViewSet(ViewSet):
    """Controller for the question marking workflow."""

    # GET: /MK/tasks/available
    @action(detail=False, methods=["get"], url_path="available")
    def available(self, request: Request, *args) -> Response:
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

    # POST: /MK/tasks/{code}
    # PATCH: /MK/tasks/{code}
    @action(detail=False, methods=["patch", "post"], url_path="(?P<code>q.+)")
    def claim_or_mark_task(self, request: Request, code: str) -> Response:
        """Attach a user to a marking task, or accept a grade and annotation.

        patch:
        Attach a user to a marking task.

        post:
        Accept a marker's grade and annotation.

        Methods:
            PATCH: see self.claim_task()
            POST: see self.mark_task()
        """
        if request.method == "PATCH":
            return self.claim_task(request, code=code)
        elif request.method == "POST":
            return self.mark_task(request, code=code)

    def claim_task(self, request: Request, *, code: str) -> Response:
        """Attach a user to a marking task and return the task's metadata.

        Reply with status 200, or 409 if someone else has claimed this
        task, or a 404 if there it not yet such a task (not scanned yet).
        If a version query parameter (e.g., "?version=2") was supplied,
        and it does not match the task, reply with a 417.  If you don't
        send version, we set it to None which means no such check will
        be made: you're claiming the task regardless of what version it is.
        """
        data = request.query_params
        version = data.get("version", None)
        if version is not None:
            version = int(version)
        try:
            papernum, question_idx = mark_task.unpack_code(code)
        except AssertionError as e:
            return _error_response(e, status.HTTP_404_NOT_FOUND)

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

    def mark_task(self, request: Request, *, code: str) -> Response:
        """Accept a marker's grade and annotation for a task.

        Returns:
            200: returns two integers, first the number of marked papers
            for this question/version and the total number of papers for
            this question/version.
            400: malformed input of some sort.
            404: no such task.
            406: integrity fail: client submitted to out-of-date task.
            409: task has changed.
            410: task is gone.
        """
        mts = MarkingTaskService()
        data = request.POST
        files = request.FILES

        plomfile = request.FILES["plomfile"]
        plomfile_data = plomfile.read().decode("utf-8")

        try:
            mark_data, annot_data = mts.validate_and_clean_marking_data(
                code, data, plomfile_data
            )
        except ObjectDoesNotExist as e:
            return _error_response(e, status.HTTP_404_NOT_FOUND)
        except ValidationError as e:
            # happens automatically but this way we keep the error msg
            return _error_response(e, status.HTTP_400_BAD_REQUEST)

        annotation_image = files["annotation_image"]
        img_md5sum = data["md5sum"]

        try:
            QuestionMarkingService.mark_task(
                code,
                user=request.user,
                marking_data=mark_data,
                annotation_data=annot_data,
                annotation_image=annotation_image,
                annotation_image_md5sum=img_md5sum,
            )
        except ValueError as e:
            return _error_response(e, status.HTTP_400_BAD_REQUEST)
        except KeyError as e:
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

        question = int_or_None(data.get("pg"))
        version = int_or_None(data.get("ver"))

        username = request.user.username
        progress = UserInfoServices.get_user_progress(username=username)
        n, m = mts.get_marking_progress(question, version)
        progress["total_tasks_marked"] = n
        progress["total_tasks"] = m
        return Response(progress, status=status.HTTP_200_OK)
