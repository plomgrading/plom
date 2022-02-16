# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2019-2021 Andrew Rechnitzer
# Copyright (C) 2020-2022 Colin B. Macdonald
# Copyright (C) 2020 Vala Vakilian

from aiohttp import web, MultipartWriter, MultipartReader

from .routeutils import authenticate_by_token, authenticate_by_token_required_fields
from .routeutils import validate_required_fields, log_request
from .routeutils import log


class MarkHandler:
    def __init__(self, plomServer):
        self.server = plomServer

    # @routes.get("/MK/maxMark")
    @authenticate_by_token_required_fields(["q", "v"])
    def MgetQuestionMark(self, data, request):
        """Retrieve the maximum mark for a question.

        Respond with status 200/416.

        Args:
            data (dict): Dictionary including user data in addition to question number
                and test version.
            request (aiohttp.web_response.Response): GET /MK/maxMark request object.

        Returns:
            aiohttp.web_response.Response: JSON with the maximum mark for
                the question and version.  Or 416 if question/version values
                out of range.  Or BadRequest (400) if question/version cannot
                be converted to integers.
        """
        question = data["q"]
        version = data["v"]
        try:
            question = int(question)
            version = int(version)
        except (ValueError, TypeError):
            raise web.HTTPBadRequest(reason="question and version must be integers")
        if question < 1 or question > self.server.testSpec["numberOfQuestions"]:
            raise web.HTTPRequestRangeNotSatisfiable(
                reason="Question out of range - please check and try again.",
            )
        if version < 1 or version > self.server.testSpec["numberOfVersions"]:
            raise web.HTTPRequestRangeNotSatisfiable(
                reason="Version out of range - please check and try again.",
            )
        maxmark = self.server.testSpec["question"][str(question)]["mark"]
        return web.json_response(maxmark, status=200)

    # @routes.get("/MK/progress")
    @authenticate_by_token_required_fields(["q", "v"])
    def MprogressCount(self, data, request):
        """Respond with the number of marked questions and the total questions tasks for user.

        Respond with status 200.

        Args:
            data (dict): Dictionary including user data in addition to question number
                and test version.
            request (aiohttp.web_request.Request): Request of type GET /MK/progress.

        Returns:
            aiohttp.web_response.Response: Includes the number of marked
                tasks and the total number of marked/unmarked tasks.
        """
        return web.json_response(
            self.server.MprogressCount(data["q"], data["v"]), status=200
        )

    # @routes.get("/MK/tasks/complete")
    @authenticate_by_token_required_fields(["user", "q", "v"])
    def MgetDoneTasks(self, data, request):
        """Retrieve data for questions which have already been graded by the user.

        Respond with status 200.

        Args:
            data (dict): Dictionary including user data in addition to
                question number and test version.
            request (aiohttp.web_response.Response): GET /MK/tasks/complete request object.

        Returns:
            aiohttp.web_response.Response: A response object including a
                list of lists with the already processed questions. The
                list involves the question string, question mark, time
                spent grading and list of tag-texts.
        """
        # return the completed list
        return web.json_response(
            self.server.MgetDoneTasks(data["user"], data["q"], data["v"]),
            status=200,
        )

    # @routes.get("/MK/tasks/available")
    @authenticate_by_token_required_fields(["q", "v"])
    def MgetNextTask(self, data, request):
        """Respond with the next task/question's string.

        Respond with status 200/204.

        Args:
            data (dict): Dictionary including user data in addition to
                question number and test version.
            request (aiohttp.web_request.Request): Request of type GET /MK/tasks/available.

        Returns:
            aiohttp.web_response.Response: A response which includes the next question's string.
                For example: q0013g1
        """
        next_task_response = self.server.MgetNextTask(data["q"], data["v"])

        next_task_available = next_task_response[0]

        # returns [True, task] or [False]
        if next_task_available:
            next_task_code = next_task_response[1]
            return web.json_response(next_task_code, status=200)
        else:
            return web.Response(status=204)  # no papers left

    # @routes.get("/MK/latex")
    @authenticate_by_token_required_fields(["user", "fragment"])
    def MlatexFragment(self, data, request):
        """Return the latex image for the string included in the request.

        Respond with status 200/406.

        Args:
            data (dict): Includes the user/token and latex string fragment.
            request (aiohttp.web_request.Request): Request of type GET /MK/latex.

        Returns:
            aiohttp.web_fileresponse.FileResponse: A response which includes the image for
                the latex string.
        """
        valid, value = self.server.MlatexFragment(data["fragment"])
        if valid:
            return web.Response(body=value, status=200)
        else:
            return web.json_response(status=406, text=value)

    # @routes.patch("/MK/tasks/{task}")
    @authenticate_by_token_required_fields(["user", "version"])
    def MclaimThisTask(self, data, request):
        """Take task number in request and return the task/question's image data as a response.

        Respond with status 200/204.

        Args:
            data (dict): A dictionary having the user/token and the version.
            request (aiohttp.web_request.Request): PATCH /MK/tasks/`question code` request object.
                This request object will include the task code.

        Returns:
            aiohttp.json_response: JSON of metadata about the images in the
               task with status 200, or 409 if someone else has claimed this
               task, or a 404 if there it not yet such a task (not scanned yet)
               or 410 if there will never be such a task, or 400/401 for
               other or authentication problems. Also 417 when the version requested does not match the version of the task.
        """

        task_code = request.match_info["task"]
        # returns either
        #   [True, image_metadata, [tag text list], integrity_check]
        #   [False, code, msg]
        retvals = self.server.MclaimThisTask(data["user"], task_code, data["version"])

        if not retvals[0]:
            code, errmsg = retvals[1:]
            if code == "other_claimed":
                raise web.HTTPConflict(reason=errmsg)
            elif code == "not_todo":
                raise web.HTTPConflict(reason=errmsg)
            elif code == "mismatch":
                raise web.HTTPExpectationFailed(reason=errmsg)
            elif code == "no_such_task":
                raise web.HTTPGone(reason=errmsg)
            elif code == "not_scanned":
                raise web.HTTPNotFound(reason=errmsg)
            else:
                raise web.HTTPBadRequest(reason=errmsg)

        return web.json_response(retvals[1:], status=200)

    # @routes.put("/MK/tasks/{task}")
    async def MreturnMarkedTask(self, request):
        """Save the graded/processes task, extract data and save to database.

        This function also responds with the number of done tasks and the total number of tasks.
        The returned statement is similar to MprogressCount.
        Respond with status 200/400/401/406/409/410.
        Log activity.

        Args:
            request (aiohttp.web_request.Request): Request of type
                PUT /MK/tasks/`question code` which includes a multipart
                object indication the marked test data. This request will
                include 3 parts including [metadata, image, plom-file].
                `image` must the the bytes of a png or jpeg file, although
                other formats might be accepted in the future.

        Returns:
            aiohttp.web_response.Response: Responses with a list including
                the number of graded tasks and the overall number of tasks.
        """

        log_request("MreturnMarkedTask", request)

        reader = MultipartReader.from_response(request)

        # Dealing with the metadata.
        part = await reader.next()
        if not part:
            raise web.HTTPBadRequest(reason="should have sent 3 parts")
        task_metadata = await part.json()

        # Validate that the dictionary has these fields.
        if not validate_required_fields(
            task_metadata,
            [
                "user",
                "token",
                "pg",
                "ver",
                "score",
                "rubrics",
                "mtime",
                "md5sum",
                "integrity_check",
                "image_md5s",
            ],
        ):
            raise web.HTTPBadRequest(reason="invalid fields in metadata")
        if not self.server.validate(task_metadata["user"], task_metadata["token"]):
            raise web.HTTPUnauthorized()

        rubrics = task_metadata["rubrics"]  # list of rubric IDs
        task = request.match_info["task"]

        # Note: if user isn't validated, we don't parse their binary junk
        # TODO: is it safe to abort during a multi-part thing?

        # Dealing with the image.
        part = await reader.next()
        if not part:
            raise web.HTTPBadRequest(reason="should have sent 3 parts")
        annotated_image = await part.read()

        # Dealing with the plom_file.
        part = await reader.next()
        if not part:
            raise web.HTTPBadRequest(reason="should have sent 3 parts")
        plomfile = await part.read()

        status, info = self.server.MreturnMarkedTask(
            task_metadata["user"],
            task,
            int(task_metadata["pg"]),
            int(task_metadata["ver"]),
            int(task_metadata["score"]),
            annotated_image,
            plomfile,
            rubrics,
            int(task_metadata["mtime"]),
            task_metadata["md5sum"],
            task_metadata["integrity_check"],
            task_metadata["image_md5s"],
        )
        if not status:
            log.warning(f"PUT:tasks/{task} giving back error: {info}")
            if info == "no_such_task":
                raise web.HTTPGone(reason=info)
            elif info == "not_owner":
                raise web.HTTPConflict(reason=info)
            elif info == "integrity_fail":
                raise web.HTTPNotAcceptable(reason=info)
            elif info == "invalid_rubric":
                raise web.HTTPNotAcceptable(reason=info)
            else:
                raise web.HTTPBadRequest(reason=str(info))

        # info is tuple of Num Done tasks, Num Totalled tasks
        return web.json_response(info, status=200)

    # @routes.get("/annotations/{number}/{question}/{edition}")
    # TODO: optionally have this integrity field?
    @authenticate_by_token_required_fields(["integrity"])
    def get_annotations(self, data, request):
        """Get the annotations of a marked question as JSON.

        Args:
            data (dict): A dictionary having the user/token, and `integrity`
                which is a checksum that can be used to check that the
                server hasn't changed state (for example added new scans to
                this question.  Pass the empty string `""` to omit such
                checks.
            request (aiohttp.web_request.Request): A GET request with url
                "/annotations/{number}/{question}/{edition}".
                `number` and `question` identify which question.
                `edition` can be used to get a particular annotation from
                the history of all annotations.  If `edition` is omitted,
                return the latest annotations.

        Returns:
            aiohttp.json_response.Response: JSON of the annotations with
                status 200, or a 404 if no such image, or 400/401 for
                authentication problems.

        Note: if you want the annotated image corresponding to these
        annotations, extract the edition from the JSON, then call
        "GET:/annotations_image/..." with that edition.

        Ownership: note that you need not be the "owner" of this task.
        Getting data back from this function does not imply permission
        to submit to this task.
        """
        number = int(request.match_info["number"])
        question = int(request.match_info["question"])
        edition = int(request.match_info["edition"])
        integrity = data.get("integrity")
        return self._get_annotations_backend(number, question, edition, integrity)

    # @routes.get("/annotations/{number}/{question}")
    @authenticate_by_token_required_fields(["integrity"])
    def get_annotations_latest(self, data, request):
        """Get the annotations of a marked question as JSON.

        See :py:method:`get_annotations`.
        """
        number = int(request.match_info["number"])
        question = int(request.match_info["question"])
        edition = None
        integrity = data.get("integrity")
        return self._get_annotations_backend(number, question, edition, integrity)

    def _get_annotations_backend(self, number, question, edition, integrity):
        if integrity == "":
            integrity = None
        results = self.server.DB.Mget_annotations(number, question, edition, integrity)
        if not results[0]:
            if results[1] == "integrity_fail":
                return web.Response(status=406)  # task changed
            elif results[1] == "no_such_task":
                return web.Response(status=410)  # task deleted
            else:
                return web.Response(status=400)  # some other error
        plomdata = results[1]
        return web.json_response(plomdata, status=200)

    # @routes.get("/annotations_image/{number}/{question}/{edition}")
    @authenticate_by_token_required_fields([])
    def get_annotations_img(self, data, request):
        """Get the image of an annotated question (a marked question).

        Args:
            data (dict): A dictionary having the user/token.
            request (aiohttp.web_request.Request): A GET request with url
                "/annotations_image/{number}/{question}/{edition}"
                `number` and `question` identify which question we want.
                `edition` can be used to get a particular annotation from
                the history of all annotations.  If `edition` is omitted,
                return the latest annotated image.

        Returns:
            aiohttp.web_response.Response: the binary image data with
                status 200, or a 404 if no such image, or 400/401 for
                authentication problems.

        Note: if you want *both* the latest annotated image and the
        latest annotations (in `.plom` format), do not simply omit the
        edition in both calls: someone might upload a new annotation
        between your calls!  Instead, call "GET:/annotations/..."
        first (without edition), then extract the edition from the `.plom`
        data.  Finally, call this with that edition.

        Ownership: note that you need not be the "owner" of this task.
        Getting data back from this function does not imply permission
        to submit to this task.
        """
        number = int(request.match_info["number"])
        question = int(request.match_info["question"])
        edition = int(request.match_info["edition"])
        return self._get_annotations_img_backend(number, question, edition)

    # @routes.get("/annotations_image/{number}/{question}")
    @authenticate_by_token_required_fields([])
    def get_annotations_img_latest(self, data, request):
        """Get the image of an annotated question (a marked question).

        See :py:method:`get_annotations_img`.
        """
        number = int(request.match_info["number"])
        question = int(request.match_info["question"])
        edition = None
        return self._get_annotations_img_backend(number, question, edition)

    def _get_annotations_img_backend(self, number, question, edition):
        results = self.server.DB.Mget_annotations(number, question, edition)
        if not results[0]:
            if results[1] == "no_such_task":
                return web.Response(status=410)  # task deleted
            else:
                return web.Response(status=400)  # some other error
        filename = results[2]
        return web.FileResponse(filename, status=200)

    # @routes.get(...)
    @authenticate_by_token_required_fields(["user"])
    def MgetOneImage(self, data, request):
        """Return one image from the database.

        Args:
            data (dict): A dictionary having the user/token.
            request (aiohttp.web_request.Request)

        Returns:
            aiohttp.web_response.Response: the binary image data, or
                a 404 response if no such image, or a 409 if wrong
                md5sum saniity check was provided.
        """
        image_id = request.match_info["image_id"]
        md5sum = request.match_info["md5sum"]

        r = self.server.DB.MgetOneImageFilename(image_id, md5sum)
        if not r[0]:
            if r[1] == "no such image":
                return web.Response(status=404)
            elif r[1] == "wrong md5sum":
                return web.Response(status=409)
            else:
                return web.Response(status=500)
        filename = r[1]
        return web.FileResponse(filename, status=200)

    # @routes.get("/MK/originalImage/{task}")
    @authenticate_by_token_required_fields([])
    def MgetOriginalImages(self, data, request):
        """Return the non-graded original images for a task/question.

        Respond with status 200/204.

        Args:
            data (dict): A dictionary having the user/token.
            request (aiohttp.web_request.Request): Request of type
                GET /MK/originalImages/`task code` which the task code
                is extracted from.

        Returns:
            aiohttp.web_response.Response: A response object with includes the multipart objects
                which wrap this task/question's original (ungraded) images.
        """

        task = request.match_info["task"]
        ok, stuff = self.server.MgetOriginalImages(task)

        if not ok:
            # TODO: "stuff" has an error message and there are several cases.
            # This API soon-to-be-deprecated?  Worth fixing or not?  Issue #1953
            return web.Response(status=204)  # no content there

        filenames = stuff
        # suboptimal but safe: read bytes instead of append(fh) (Issue #1877)
        with MultipartWriter("images") as mpwriter:
            for f in filenames:
                with open(f, "rb") as fh:
                    b = fh.read()
                mpwriter.append(b)
            return web.Response(body=mpwriter, status=200)

    # @routes.get("/tags/{task}")
    @authenticate_by_token_required_fields([])
    def get_tags_of_task(self, data, request):
        """List the tags for a task.

        Args:
            data (dict): user, token.

        Returns:
            aiohttp.web_response.json_response: list of strings, one for each tag text.
        """
        task = request.match_info["task"]
        tag_list = self.server.DB.MgetTagsOfTask(task)
        return web.json_response(tag_list)

    # @routes.patch("/tags/{task}")
    @authenticate_by_token_required_fields(["user", "tag_text"])
    def add_tag(self, data, request):
        """Add a tag for a task.

        Respond with status 200/406/410.

        Args:
            data (dict): user, token and the text for the given tag (str).

        Returns:
            aiohttp.web_response.Response: 200 on success or
                HTTPNotAcceptable (406) if tag is invalid
                HTTPGone (410) if cannot find task

        """
        task = request.match_info["task"]
        tag_text = data["tag_text"]
        if not self.server.checkTagTextValid(tag_text):
            raise web.HTTPNotAcceptable(reason="Text contains disallowed characters.")

        if not self.server.add_tag(data["user"], task, tag_text):
            raise web.HTTPGone(reason="No such task.")
        return web.Response(status=200)

    # @routes.delete("/tags/{task}")
    @authenticate_by_token_required_fields(["user", "tag_text"])
    def remove_tag(self, data, request):
        """Remove a tag from a task.

        Respond with status 200/410.

        Args:
            data (dict): user, token and the text of the tag (str).

        Returns:
            aiohttp.web_response.Response: 200 on success or
                HTTPGone (410) if no such tag.
        """
        task = request.match_info["task"]
        tag_text = data["tag_text"].strip()

        if not self.server.remove_tag(task, tag_text):
            raise web.HTTPGone(reason="No such tag")
        return web.Response(status=200)

    # @routes.get("/all_tags")
    @authenticate_by_token_required_fields(["user"])
    def get_all_tags(self, data, request):
        """Get list of all tags in system.

        Respond with status 200.

        Args:
            data (dict): user, token.

        Returns:
            aiohttp.web_response.Response: 200 with list of tags each encoded as (key, text)
        """
        tag_list = self.server.MgetAllTags()
        return web.json_response(tag_list)

    # @routes.patch("/tags")
    @authenticate_by_token_required_fields(["user", "tag_text"])
    def create_new_tag(self, data, request):
        """Get list of all tags in system.

        Respond with status 200/406/409.

        Args:
            data (dict): user, token, tag_text.

        Returns:
            aiohttp.web_response.Response: 200 with key for new tag or
                HTTPNotAcceptable if tag text is not acceptable or
                HTTPConflict if tag already in system.
        """
        if not self.server.checkTagTextValid(data["tag_text"]):
            raise web.HTTPNotAcceptable(reason="Text contains disallowed characters")
        success, tag_key = self.server.McreateNewTag(data["user"], data["tag_text"])
        if success:
            return web.json_response(tag_key)
        else:
            raise request.HTTPConflict(reason="Tag already in system")

    # @routes.get("/tags/{task}")
    @authenticate_by_token_required_fields([])
    def get_tags(self, data, request):
        """List the tags for a task.

        Args:
            data (dict): user, token.

        Returns:
            aiohttp.web_response.json_response: list of strings, one for each
                tag, or HTTPConflict (409) if user not permitted to get tags
                for that paper.
        """
        task = request.match_info["task"]
        tags = self.server.DB.MgetTags(task)
        if tags is None:
            # TODO: wrong thing?  not conflict, badrequest
            raise web.HTTPConflict(reason=f"Not such task {task}")
        tags = tags.split()
        return web.json_response(tags)

    # @routes.get("/MK/whole/{number}")
    @authenticate_by_token_required_fields([])
    def MgetWholePaper(self, data, request):
        """Return the entire paper which includes the given question.

        Respond with status 200/404.

        Args:
            data (dict): A dictionary having the user/token.
            request (aiohttp.web_request.Request): GET /MK/whole/`test_number`/`question_number`.

        Returns:
            aiohttp.web_response.Response: Responds with a multipart
                writer which includes all the images for the exam which
                includes this question.
        """
        test_number = request.match_info["number"]
        question_number = request.match_info["question"]

        # return [True, pageData, f1, f2, f3, ...] or [False]
        # 1. True/False for operation status.
        # 2. A list of lists, documented elsewhere (TODO: I hope)
        # 3. 3rd element onward: paths for each page of the paper in server.
        whole_paper_response = self.server.MgetWholePaper(test_number, question_number)

        if not whole_paper_response[0]:
            return web.Response(status=404)

        pages_data = whole_paper_response[1]
        filenames = whole_paper_response[2:]
        # suboptimal but safe: read bytes instead of append(fh) (Issue #1877)
        with MultipartWriter("images") as mpwriter:
            mpwriter.append_json(pages_data)
            for f in filenames:
                with open(f, "rb") as fh:
                    b = fh.read()
                mpwriter.append(b)
            return web.Response(body=mpwriter, status=200)

    # @routes.get("/MK/TMP/whole/{number}/{question}")
    @authenticate_by_token_required_fields([])
    def MgetWholePaperMetadata(self, data, request):
        """Return the metadata for all images associated with a paper

        Respond with status 200/404.

        Args:
            data (dict): A dictionary having the user/token.
            request (aiohttp.web_request.Request): GET /MK/whole/`test_number`/`question_number`.

        Returns:
            aiohttp.web_response.Response: JSON data, a list of dicts
                where each dict has keys:
                pagename, md5, included, order, id, orientation, server_path
                as documented below.

        The list of dicts (we think of them as rows) have the following
        contents:

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

        `included`
            boolean, did the server *originally* have this page
            included in question number `question`?.  Note that clients
            may pull other pages into their annotating; you can only
            rely on this information for initializing a new annotating
            session.  If you're e.g., editing an existing annotation,
            you should rely on the info from that existing annotation
            instead of this.

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
        test_number = request.match_info["number"]
        # this is used to determine the true/false "included" info
        question_number = request.match_info["question"]

        # return [True, pageData, f1, f2, f3, ...] or [False]
        # 1. True/False for operation status.
        # 2. A list of lists, as doc'd above
        # 3. 3rd element onward: paths for each page of the paper in server.
        r = self.server.MgetWholePaper(test_number, question_number)

        if not r[0]:
            return web.Response(status=404)

        all_pages_paths = r[2:]
        assert len(r[1]) == len(all_pages_paths)
        rownames = ("pagename", "md5", "included", "order", "id", "server_path")
        pages_data = []
        for i, row in enumerate(r[1]):
            pages_data.append({k: v for k, v in zip(rownames, row)})
            pages_data[i]["server_path"] = all_pages_paths[i]
            # For now, server has no orientation data but callers expect it
            pages_data[i]["orientation"] = 0
        return web.json_response(pages_data, status=200)

    # @routes.get("/MK/allMax")
    @authenticate_by_token
    def MgetAllMax(self):
        """Respond with information on max mark possible for each question in the exam.

        Respond with status 200/404.

        Returns:
            aiohttp.web_response.Response: A response which includes a dictionary
                for the highest mark possible for each question of the exam.
        """
        return web.json_response(self.server.MgetAllMax(), status=200)

    # @routes.patch("/MK/review")
    @authenticate_by_token_required_fields(["testNumber", "questionNumber", "version"])
    def MreviewQuestion(self, data, request):
        """Confirm the question review done on plom-manager.

        Respond with status 200/404.

        Args:
            data (dict): Dictionary including user data in addition to question number
                and test version.
            request (aiohttp.web_request.Request): Request of type PATCH /MK/review .

        Returns:
            aiohttp.web_response.Response: Empty status response indication if the question
                review was successful.
        """

        if self.server.MreviewQuestion(
            data["testNumber"], data["questionNumber"], data["version"]
        ):
            return web.Response(status=200)
        else:
            return web.Response(status=404)

    # @routes.patch("/MK/revert/{task}")
    # TODO: Deprecated.
    # TODO: Should be removed.
    @authenticate_by_token_required_fields(["user"])
    def MrevertTask(self, data, request):
        # only manager can do this
        task = request.match_info["task"]
        if not data["user"] == "manager":
            return web.Response(status=401)  # malformed request.
        rval = self.server.MrevertTask(task)
        if rval[0]:
            return web.Response(status=200)
        elif rval[1] == "NAC":  # nothing to be done here.
            return web.Response(status=204)
        else:  # cannot find that task
            return web.Response(status=404)

    def setUpRoutes(self, router):
        """Adds the response functions to the router object.

        Args:
            router (aiohttp.web_urldispatcher.UrlDispatcher): Router object which we will add the response functions to.
        """
        router.add_get("/MK/allMax", self.MgetAllMax)
        router.add_get("/MK/maxMark", self.MgetQuestionMark)
        router.add_get("/MK/progress", self.MprogressCount)
        router.add_get("/MK/tasks/complete", self.MgetDoneTasks)
        router.add_get("/MK/tasks/available", self.MgetNextTask)
        router.add_get("/MK/latex", self.MlatexFragment)
        router.add_patch("/MK/tasks/{task}", self.MclaimThisTask)
        router.add_put("/MK/tasks/{task}", self.MreturnMarkedTask)
        router.add_get("/MK/images/{image_id}/{md5sum}", self.MgetOneImage)
        router.add_get("/MK/originalImages/{task}", self.MgetOriginalImages)
        router.add_get("/tags", self.get_all_tags)
        router.add_get("/tags/{task}", self.get_tags_of_task)
        router.add_patch("/tags/{task}", self.add_tag)
        router.add_delete("/tags/{task}", self.remove_tag)
        router.add_patch("/tags", self.create_new_tag)
        router.add_get("/MK/whole/{number}/{question}", self.MgetWholePaper)
        router.add_get("/MK/TMP/whole/{number}/{question}", self.MgetWholePaperMetadata)
        router.add_get("/annotations/{number}/{question}", self.get_annotations_latest)
        router.add_get(
            "/annotations/{number}/{question}/{edition}", self.get_annotations
        )
        router.add_get(
            "/annotations_image/{number}/{question}", self.get_annotations_img_latest
        )
        router.add_get(
            "/annotations_image/{number}/{question}/{edition}", self.get_annotations_img
        )
        router.add_patch("/MK/review", self.MreviewQuestion)
        router.add_patch("/MK/revert/{task}", self.MrevertTask)
