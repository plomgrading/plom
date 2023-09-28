# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2022-2023 Colin B. Macdonald
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2023 Julian Lapenna

from typing import Optional

from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist
from rest_framework import status
from rest_framework.viewsets import ViewSet
from rest_framework.decorators import action
from rest_framework.response import Response

from Mark.services import QuestionMarkingService, MarkingTaskService
from .utils import _error_response


class QuestionMarkingViewSet(ViewSet):
    """Controller for the question marking workflow."""

    @action(detail=False, methods=["get"], url_path="available")
    def available(self, request, *args):
        """Get the next marking task.

        get:
        Responds with a code for the next available marking task.

        The behaviour is influenced by various options.  A confusing case is
        ``tag`` which is a *preference* and not a *requiremennt*.
        You can still receive tasks that do not match the tag.

        Returns:
            200: An available task exists, returns the task code as a string.
            204: There are no available tasks.
        """
        data = request.query_params
        question: Optional[int] = data.get("q")
        version: Optional[int] = data.get("v")
        # TODO: someday rename above in transit as well: a later problem
        # TODO: fix this while also adding `max_paper_num`
        _ = data.get("above")
        if _ is not None:
            _ = int(_)
        min_paper_num: Optional[int] = _
        tag: Optional[str] = data.get("tag")

        task = QuestionMarkingService(
            question=question,
            version=version,
            user=request.user,
            min_paper_num=min_paper_num,
            tag=tag,
        ).get_first_available_task()

        if tag and not task:
            # didn't find anything tagged, so try again without
            task = QuestionMarkingService(
                question=question,
                version=version,
                user=request.user,
                min_paper_num=min_paper_num,
            ).get_first_available_task()

        if not task:
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(task.code, status=status.HTTP_200_OK)

    @action(detail=False, methods=["patch", "post"], url_path="(?P<code>q.+)")
    def claim_or_mark_task(self, request, code):
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

    def claim_task(self, request, code):
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
                service.assign_task_to_user()
                question_data = service.get_page_data()
                tags = service.get_tags()

            return Response([question_data, tags, service.task_pk])
        except ValueError as e:
            return _error_response(e, status.HTTP_404_NOT_FOUND)
        except RuntimeError as e:
            return _error_response(e, status.HTTP_409_CONFLICT)

    def mark_task(self, request, code):
        """Accept a marker's grade and annotation for a task."""
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
        except ValidationError as e:
            # TODO: explicitly throwing server 500 is ok?  Better to just remove this block?
            return _error_response(e, status.HTTP_500_INTERNAL_SERVER_ERROR)

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
            return _error_response(str(e), status.HTTP_400_BAD_REQUEST)

        return Response(
            [mts.get_n_marked_tasks(), mts.get_n_total_tasks()],
            status=status.HTTP_200_OK,
        )
