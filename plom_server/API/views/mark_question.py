# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2022-2024 Colin B. Macdonald
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2023 Julian Lapenna

from __future__ import annotations

from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist
from rest_framework import status
from rest_framework.viewsets import ViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.request import Request

from Mark.services import QuestionMarkingService, MarkingTaskService
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
            return _error_response(e, status.HTTP_406_NOT_ACCEPTABLE)

        _tag: str | None = data.get("tags")
        if _tag:
            tags = _tag.split(",")
        else:
            tags = []

        task = QuestionMarkingService(
            question=question,
            version=version,
            user=request.user,
            min_paper_num=min_paper_num,
            max_paper_num=max_paper_num,
        ).get_first_available_task(tags=tags)

        if not task and tags:
            # didn't find anything tagged, so try again without
            task = QuestionMarkingService(
                question=question,
                version=version,
                user=request.user,
                min_paper_num=min_paper_num,
                max_paper_num=max_paper_num,
            ).get_first_available_task()

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
            return self.claim_task(request, code)
        elif request.method == "POST":
            return self.mark_task(request, code)

    def claim_task(self, request: Request, code: str) -> Response:
        """Attach a user to a marking task and return the task's metadata.

        Reply with status 200, or 409 if someone else has claimed this
        task, or a 404 if there it not yet such a task (not scanned yet)
        or 410 if there will never be such a task.

        Notes: legacy would use 417 when the version requested does not
        match the version of the task.  But I think we ignore the version.
        """
        service = QuestionMarkingService(code=code, user=request.user)
        try:
            with transaction.atomic():
                task = service._get_task_for_update()
                MarkingTaskService.assign_task_to_user(task.pk, request.user)
                question_data = service.get_page_data()
                tags = MarkingTaskService().get_tags_for_task(code)

            return Response([question_data, tags, service.task_pk])
        except (ValueError, ObjectDoesNotExist) as e:
            return _error_response(e, status.HTTP_404_NOT_FOUND)
        except RuntimeError as e:
            return _error_response(e, status.HTTP_409_CONFLICT)

    def mark_task(self, request: Request, code: str) -> Response:
        """Accept a marker's grade and annotation for a task.

        Returns:
        (200): returns two integers, first the number of marked papers
            for this question/version and the total number of papers for
            this question/version.
        """
        mts = MarkingTaskService()
        data = request.POST
        files = request.FILES

        plomfile = request.FILES["plomfile"]
        plomfile_data = plomfile.read().decode("utf-8")

        try:
            mark_data, annot_data, rubrics_used = mts.validate_and_clean_marking_data(
                request.user, code, data, plomfile_data
            )
        except ObjectDoesNotExist as e:
            return _error_response(e, status.HTTP_404_NOT_FOUND)
        except RuntimeError as e:
            return _error_response(e, status.HTTP_409_CONFLICT)

        annotation_image = files["annotation_image"]
        img_md5sum = data["md5sum"]

        service = QuestionMarkingService(
            code=code,
            annotation_data=annot_data,
            marking_data=mark_data,
            user=request.user,
            annotation_image=annotation_image,
            annotation_image_md5sum=img_md5sum,
        )

        try:
            service.mark_task()
        except ValueError as e:
            return _error_response(e, status.HTTP_400_BAD_REQUEST)
        except RuntimeError as e:
            return _error_response(e, status.HTTP_409_CONFLICT)

        def int_or_None(x):
            return None if x is None else int(x)

        question = int_or_None(data.get("pg"))
        version = int_or_None(data.get("ver"))

        return Response(
            mts.get_marking_progress(question=question, version=version),
            status=status.HTTP_200_OK,
        )
