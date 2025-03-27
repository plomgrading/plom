# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2022-2025 Colin B. Macdonald
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2024 Bryan Tanady

from rest_framework.views import APIView
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework import serializers, status

from django.core.exceptions import ObjectDoesNotExist
from django.http import FileResponse

from plom_server.Finish.services import SolnImageService
from plom_server.Mark.services import (
    mark_task,
    MarkingTaskService,
    PageDataService,
    MarkingStatsService,
)
from plom_server.Papers.services import SpecificationService
from plom_server.Papers.models import Image

from plom_server.Progress.services import UserInfoServices

from .utils import _error_response


class QuestionMaxMark(APIView):
    """Return the max mark for a given question.

    Returns:
        (200): returns the maximum number of points for a question
        (416): question value out of range
    """

    def get(self, request: Request, *, question: int) -> Response:
        """Get the max mark for a given question."""
        try:
            max_mark = SpecificationService.get_question_mark(question)
            return Response(max_mark)
        except ObjectDoesNotExist as e:
            return _error_response(
                f"Question {question} out of range: {e}",
                status.HTTP_416_REQUESTED_RANGE_NOT_SATISFIABLE,
            )


# GET: /MK/progress/{question}/{version}
class MarkingProgress(APIView):
    """Responds with dict of information about progress and quota status.

    Returns:
        (200): returns a dict of info about this question version and
            user including "total_tasks_marked", "total_tasks".
            Also includes information about the user's progress including
            their quota status in "user_tasks_claimed",
            "user_tasks_marked", "user_has_quota_limit", "user_quota_limit".
        (416): question values out of range: NOT IMPLEMENTED YET.
            (In legacy, this was thrown by the backend).  Here, currently
            you just get zeros, which seems fine: maybe we don't need this
            error handling?

    If there are no tasks, returns zero in "total tasks".
    """

    def get(self, request: Request, *, question: int, version: int) -> Response:
        """Get dict of information about progress and quota status."""
        # TODO: consider version/question into query params to make them optional
        username = request.user.username
        progress = UserInfoServices.get_user_progress(username=username)
        mts = MarkingTaskService()
        n, m = mts.get_marking_progress(question, version)
        progress["total_tasks_marked"] = n
        progress["total_tasks"] = m
        return Response(progress, status=status.HTTP_200_OK)


# GET: /MK/tasks/all
class GetTasks(APIView):
    """Retrieve data for tasks.

    Respond with status 200.

    Returns:
        List of dicts of info for each task, as documented elsewhere.
        An empty list might be returned if no tasks.
        This is potentially a lot of data, perhaps a megabyte of json
        for 4000 papers.

    Note that this might leak info to non-lead-markers, we may want non-lead-markers
    to only be able to query their own tasks.
    """

    def get(self, request: Request) -> Response:
        """Get data for tasks."""
        data = request.query_params
        question_idx = data.get("q")
        version = data.get("v")
        username = data.get("username")
        # TODO: much more optional things we could support: tag, paper_min, paper_max
        # see progress_task_annot.py, lots of extensibility possible here in future.
        # TODO: priority might be useful for client

        data = MarkingStatsService().filter_marking_task_annotation_info(
            question_idx=question_idx,
            version=version,
            username=username,
        )
        return Response(data, status=status.HTTP_200_OK)


# PATCH: /MK/tasks/{code}/reassign/{new_username}
class ReassignTask(APIView):
    """Reassign a task to another user.

    Returns:
        200: returns json of True.
        404: task or user not found.
        406: request not acceptable from calling user, e.g.,
            not lead marker or manager.
    """

    def patch(self, request: Request, *, code: str, new_username: str) -> Response:
        """Reassign a task to another user."""
        calling_user = request.user
        group_list = list(request.user.groups.values_list("name", flat=True))
        if not ("lead_marker" in group_list or "manager" in group_list):
            return _error_response(
                f"You ({calling_user}) cannot reassign tasks because "
                "you are not a lead marker or manager",
                status.HTTP_406_NOT_ACCEPTABLE,
            )

        try:
            task = MarkingTaskService().get_task_from_code(code)
            task_pk = task.pk
        except (ValueError, RuntimeError) as e:
            return _error_response(e, status.HTTP_404_NOT_FOUND)

        try:
            MarkingTaskService.reassign_task_to_user(
                task_pk,
                new_username=new_username,
                calling_user=calling_user,
                unassign_others=True,
            )
        except ValueError as e:
            return _error_response(e, status.HTTP_404_NOT_FOUND)

        return Response(True, status=status.HTTP_200_OK)


# PATCH: /MK/tasks/{code}/reset
class ResetTask(APIView):
    """Reset a task, making all annotations outdating and putting it back into the pool for remarking from scratch.

    Returns:
        200: returns json of True.
        404: task not found.
        406: request not acceptable from calling user, e.g.,
            not lead marker or manager.
    """

    def patch(self, request: Request, *, code: str) -> Response:
        """Reset a task."""
        calling_user = request.user
        group_list = list(request.user.groups.values_list("name", flat=True))
        if not ("lead_marker" in group_list or "manager" in group_list):
            return _error_response(
                f"You ({calling_user}) cannot reassign tasks because "
                "you are not a lead marker or manager",
                status.HTTP_406_NOT_ACCEPTABLE,
            )

        try:
            papernum, question_idx = mark_task.unpack_code(code)
        except AssertionError as e:
            return _error_response(e, status.HTTP_404_NOT_FOUND)

        try:
            MarkingTaskService().set_paper_marking_task_outdated(papernum, question_idx)
        except ValueError as e:
            return _error_response(e, status.HTTP_404_NOT_FOUND)

        return Response(True, status=status.HTTP_200_OK)


# GET: /pagedata/{papernum}
# GET: /pagedata/{papernum}/context/{questionidx}
class MgetPageDataQuestionInContext(APIView):
    """Get page metadata for a paper optionally with a question highlighted.

    APIs backed by this routine return a JSON response with a list of
    dicts, where each dict has keys: `pagename`, `md5`, `included`,
    `order`, `id`, `orientation`, `server_path` as documented below.

    This routine returns all pages, including ID pages, DNM pages and
    various sorts of extra pages.

    A 409 is returned with an explanation if paper number not found.

    The list of dicts (we think of them as rows) have the keys:

    `pagename`
        A string something like `"t2"`.  Reasonable to use
        as a thumbnail label for the image or in other cases where
        a very short string label is required.

    `md5`
        A string of the md5sum of the image.

    `id`
        an integer like 19.  This is the key in the database to
        the image of this page.  It is (I think) possible to have
        two pages pointing to the same image, in which case the md5
        and the id could be repeated.  TODO: determine if this only
        happens b/c of bugs/upload issues or if its a reasonably
        normal state.
        Note this is nothing to do with "the ID page", that is the page
        where assessment writers put their name and other info.

    `order`
        None or an integer specifying the relative ordering of
        pages within a question.  As with `included`,
        this information only reflects the initial (typically
        scan-time) ordering of the images.  If its None, server has
        no info about what order might be appropriate, for example
        because this image is not thought to belong in `question`.

    `orientation`
        relative to the natural orientation of the image.
        This is an integer for the degrees of rotation.  Probably
        only multiples of 90 work and perhaps only [0, 90, 180, 270]
        but could/should (TODO) be generalized for arbitrary
        rotations.  This should be applied *after* any metadata
        rotations from inside the file instead (such as jpeg exif
        orientation).  As with `included` and `order`, this is only
        the initial state.  Clients may rotate images and that
        information belongs their annotation.

    `server_path`
        a string of a path and filename where the server
        might have the file stored, such as
        `"pages/originalPages/t0004p02v1.86784dd1.png"`.
        This is guaranteed unique (such as by the random bit before
        `.png`).  It is *not* guaranteed that the server actually
        stores the file in this location, although the current
        implementation does.

    `included`
        boolean, did the server *originally* have this page
        included in question index `question`?.  Note that clients
        may pull other pages into their annotating; you can only
        rely on this information for initializing a new annotating
        session.  If you're e.g., editing an existing annotation,
        you should rely on the info from that existing annotation
        instead of this.

    Example::

        [
          {'pagename': 't2',
           'md5': 'e4e131f476bfd364052f2e1d866533ea',
           'included': False,
           'order': None,
           'id': 19',
           'orientation': 0
           'server_path': 'pages/originalPages/t0004p02v1.86784dd1.png',
          },
          {'pagename': 't3',
           'md5': 'a896cb05f2616cb101df175a94c2ef95',
           'included': True,
           'order': 1,
           'id': 20,
           'orientation': 270
           'server_path': 'pages/originalPages/t0004p03v2.ef7f9754.png',
          }
        ]
    """

    def get(
        self, request: Request, *, papernum: int, questionidx: int | None = None
    ) -> Response:
        """Get page metadata for a paper optionally with a question highlighted."""
        service = PageDataService()

        try:
            # we need include_idpage here b/c this APIView Class serves two different
            # API calls: one of which wants all pages.  Its also documented above that
            # callers who don't want to see the ID page (generally b/c Plom does
            # anonymous grading) should filter this out.  This is the current behaviour
            # of the Plom Client UI tool.
            page_metadata = service.get_question_pages_metadata(
                papernum,
                question=questionidx,
                include_idpage=True,
                include_dnmpages=True,
            )
        except ObjectDoesNotExist as e:
            return _error_response(
                f"Paper {papernum} does not exist: {e}", status.HTTP_409_CONFLICT
            )
        return Response(page_metadata, status=status.HTTP_200_OK)


# GET: /MK/images/{image_id}/{hash}
class MgetOneImage(APIView):
    """Get a page image from the server."""

    def get(self, request: Request, *, pk: int, hash: str) -> Response:
        """Get a page image."""
        pds = PageDataService()
        try:
            img_django_file = pds.get_page_image(pk, img_hash=hash)
            return FileResponse(img_django_file, status=status.HTTP_200_OK)
        except Image.DoesNotExist:
            return _error_response("Image does not exist.", status.HTTP_400_BAD_REQUEST)


# GET: /annotations/{paper}/{question}
class MgetAnnotations(APIView):
    """Get the latest annotations for a question.

    TODO: implement "edition"?
    # GET: /annotations/{paper}/{question}/{edition}

    TODO: The legacy server sends 410 for "task deleted", and the client
    messenger is documented as expecting 406/410/416.
    I suspect here we have folded the "task deleted" case into the 404.

    Returns:
        200: the annotation data.
        404: no such task (i.e., no such paper) or no annotations for the
            task if it exists.
        406: the task has been modified, perhaps even during this call?
            TODO: some atomic operation would prevent this?
    """

    def get(self, request: Request, *, paper: int, question: int) -> Response:
        """Get the latest annotations."""
        mts = MarkingTaskService()
        try:
            annotation = mts.get_latest_annotation(paper, question)
        except ObjectDoesNotExist as e:
            return _error_response(
                f"No annotations for paper {paper} question {question}: {e}",
                status.HTTP_404_NOT_FOUND,
            )
        except ValueError as e:
            return _error_response(e, status.HTTP_404_NOT_FOUND)
        annotation_task = annotation.task
        annotation_data = annotation.annotation_data

        # TODO is this really needed?  Issue #3283.
        try:
            latest_task = mark_task.get_latest_task(paper, question)
        except ObjectDoesNotExist as e:
            # Possibly should be 410?  see baseMessenger.py
            return _error_response(e, status.HTTP_404_NOT_FOUND)

        if latest_task != annotation_task:
            return _error_response(
                "Integrity error: task has been modified by server.",
                status.HTTP_406_NOT_ACCEPTABLE,
            )

        annotation_data["user"] = annotation.user.username
        annotation_data["annotation_edition"] = annotation.edition
        annotation_data["annotation_reference"] = annotation.pk

        return Response(annotation_data, status=status.HTTP_200_OK)


# GET: /annotations_image/{paper}/{question}
# GET: /annotations_image/{paper}/{question}/{edition}
class MgetAnnotationImage(APIView):
    """Get an annotation image.

    Callers ask for paper number, question index (one-indexed) and
    optionally edition.  If edition is omitted, they get the latest.
    The edition must be for a valid (non-out-of-date) task: for example
    if someone adds new papers then this call could fail (currently
    with 404 but maybe should be 410, see discussion below).

    I think there is still a race condition because of the above::

      1. client asks for latest annotation, gets json.
      2. client looks and sees edition 1.
      3. During 2, new papers are uploaded AND very quickly someone
         annotates.
      4. client adks for edition 1.  They get the new annotated image
         which does not match their json data.  This would require
         precise timing and a VERY slow client...  "Anyone that unlucky
         has already been hit by a bus" -- Jim Wilkinson.

    The fix here is probably to use a id/pk-based image get.

    TODO: The legacy server sends 410 for "task deleted", and the client
    messenger is documented as expecting 406/410/416 (although the legacy
    server doesn't seem to send 406/416 for annotation image calls).
    I suspect here we have folded the "task deleted" case into the 404.

    TODO: In the future, we might want to ensure that the username has
    permission to look at these annotations: currently this is not
    enforced or expected by the client.

    Returns:
        200: the image as a file.
        404: no such task (i.e., no such paper) or no annotations for the
            task if it exists, or wrong edition, or there was no latest
            annotation, e.g., b/c it was reset.
        406: the task has been modified, perhaps even during this call?
            TODO: some atomic operation would prevent this?
    """

    def get(
        self, request: Request, *, paper: int, question: int, edition: int | None = None
    ) -> Response:
        """Get an annotation image."""
        mts = MarkingTaskService()
        if edition is not None:
            try:
                annotation = mts.get_annotation_by_edition(paper, question, edition)
            except ObjectDoesNotExist as e:
                return _error_response(
                    f"No edition={edition} annotations for paper {paper}"
                    f" question idx {question}: {e}",
                    status.HTTP_404_NOT_FOUND,
                )
            return FileResponse(annotation.image.image, status=status.HTTP_200_OK)

        try:
            annotation = mts.get_latest_annotation(paper, question)
        except ObjectDoesNotExist as e:
            return _error_response(
                f"No annotations for paper {paper} question idx {question}: {e}",
                status.HTTP_404_NOT_FOUND,
            )
        except ValueError as e:
            return _error_response(e, status.HTTP_404_NOT_FOUND)
        annotation_task = annotation.task
        annotation_image = annotation.image

        # TODO is this really needed?  Issue #3283.
        try:
            latest_task = mark_task.get_latest_task(paper, question)
        except ObjectDoesNotExist as e:
            return _error_response(e, status.HTTP_404_NOT_FOUND)
        if latest_task != annotation_task:
            return _error_response(
                "Integrity error: task has been modified by server.",
                status.HTTP_406_NOT_ACCEPTABLE,
            )
        return FileResponse(annotation_image.image, status=status.HTTP_200_OK)


class TagsFromCodeView(APIView):
    """Handle getting and setting tags for marking tasks."""

    def get(self, request: Request, *, code: str) -> Response:
        """Get all of the tags for a particular task.

        Args:
            request: an http request.

        Keyword Args:
            code: question/paper code for a task.

        Returns:
            200: list of tag texts

        Raises:
            406: Invalid task code
            404: Task is not found
        """
        mts = MarkingTaskService()
        try:
            return Response(mts.get_tags_for_task(code), status=status.HTTP_200_OK)
        except ValueError as e:
            return _error_response(e, status.HTTP_406_NOT_ACCEPTABLE)
        except RuntimeError as e:
            return _error_response(e, status.HTTP_404_NOT_FOUND)

    def patch(self, request: Request, *, code: str) -> Response:
        """Add a tag to a task. If the tag does not exist in the database, create it as a side effect.

        Args:
            request: an http request.

        Keyword Args:
            code: question/paper code for a task.

        Returns:
            200: OK response

        Raises:
            406: Invalid tag text
            404: Task is not found
            410: Invalid task code

        TODO: legacy uses 204 in the case of "already tagged", which
        I think we just silently accept and return 200.
        """
        mts = MarkingTaskService()
        tag_text = request.data["tag_text"]
        tag_text = tag_text.strip()
        user = request.user

        try:
            mts.add_tag_text_from_task_code(tag_text, code, user=user)
        except ValueError as e:
            return _error_response(e, status.HTTP_410_GONE)
        except RuntimeError as e:
            return _error_response(e, status.HTTP_404_NOT_FOUND)
        except serializers.ValidationError as e:
            return _error_response(e, status.HTTP_406_NOT_ACCEPTABLE)
        return Response(status=status.HTTP_200_OK)

    def delete(self, request: Request, *, code: str) -> Response:
        """Remove a tag from a task.

        Args:
            request: a Request object with ``tag_text`` (`str`) as a
                data field.

        Keyword Args:
            code: question/paper code for a task.

        Returns:
            200: OK response

        Raises:
            409: Invalid task code, no such tag, or this task does not
                have this tag.
            404: Task is not found
        """
        mts = MarkingTaskService()
        tag_text = request.data["tag_text"]
        tag_text = tag_text.strip()

        try:
            mts.remove_tag_text_from_task_code(tag_text, code)
        except ValueError as e:
            return _error_response(e, status.HTTP_409_CONFLICT)
        except RuntimeError as e:
            return _error_response(e, status.HTTP_404_NOT_FOUND)
        return Response(status=status.HTTP_200_OK)


class GetAllTags(APIView):
    """Respond with all of the tags in the server."""

    def get(self, request: Request) -> Response:
        """Get all the tags."""
        mts = MarkingTaskService()
        return Response(mts.get_all_tags(), status=status.HTTP_200_OK)


class GetSolutionImage(APIView):
    """Get a solution image from the server."""

    def get(self, request: Request, *, question: int, version: int) -> Response:
        """Get a solution image."""
        try:
            return FileResponse(SolnImageService().get_soln_image(question, version))
        except ObjectDoesNotExist:
            return _error_response("Image does not exist.", status.HTTP_404_NOT_FOUND)
