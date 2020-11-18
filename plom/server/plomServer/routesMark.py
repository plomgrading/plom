# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2019-2020 Andrew Rechnitzer
# Copyright (C) 2020 Colin B. Macdonald
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
        """Retreive the maximum mark for a question.

        Respond with status 200/416.

        Args:
            data (dict): Dictionary including user data in addition to question number
                and test version.
            request (aiohttp.web_response.Response): GET /MK/maxMark request object.

        Returns:
            aiohttp.web_response.Response: Response object which has the
                maximum mark for the question.
        """
        question_number = data["q"]
        test_version = data["v"]
        valid_question, maximum_mark_response = self.server.MgetQuestionMax(
            question_number, test_version
        )

        if valid_question:
            return web.json_response(maximum_mark_response, status=200)
        elif maximum_mark_response == "QE":  # Check if the question was out of range
            # pg out of range
            return web.Response(
                text="Question out of range - please check before trying again.",
                status=416,
            )
        elif maximum_mark_response == "VE":  # Check if the version was out of range
            # version our of range
            return web.Response(
                text="Version out of range - please check before trying again.",
                status=416,
            )

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
                spent grading and tag string.
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
        latex_response = self.server.MlatexFragment(data["user"], data["fragment"])
        latex_valid = latex_response[0]

        if latex_valid:
            latex_image_path = latex_response[1]
            return web.FileResponse(latex_image_path, status=200)
        else:
            return web.Response(status=406)  # a latex error

    # @routes.patch("/MK/tasks/{task}")
    @authenticate_by_token_required_fields(["user"])
    def MclaimThisTask(self, data, request):
        """Take task number in request and return the task/question's image data as a response.

        Respond with status 200/204.

        Args:
            data (dict): A dictionary having the user/token.
            request (aiohttp.web_request.Request): PATCH /MK/tasks/`question code` request object.
                This request object will include the task code.

        Returns:
            aiohttp.web_response.json_response: metadata about the images.
        """

        task_code = request.match_info["task"]
        # returns either
        #   [True, image_metadata, tags, integrity_check]
        #   [False]
        retvals = self.server.MclaimThisTask(data["user"], task_code)

        if not retvals[0]:
            return web.Response(status=204)  # that task already taken.
        return web.json_response(retvals[1:], status=200)

    # @routes.delete("/MK/tasks/{task}")
    @authenticate_by_token_required_fields(["user"])
    def MdidNotFinishTask(self, data, request):
        """Assign tasks that are not graded (untouched) as unfinished in the database.

        Respond with status 200.

        Args:
            data (dict): Includes the user/token and task code.
            request (aiohttp.web_request.Request): Request of type DELETE /MK/tasks/`question code`.

        Returns:
            aiohttp.web_response.Response: Returns a success status indicating the task is unfinished.
        """

        task_code = request.match_info["task"]
        self.server.MdidNotFinish(data["user"], task_code)

        return web.json_response(status=200)

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

        Returns:
            aiohttp.web_response.Response: Responses with a list including the number of
                graded tasks and the overall number of tasks.
        """

        log_request("MreturnMarkedTask", request)

        reader = MultipartReader.from_response(request)

        # Dealing with the metadata.
        task_metadata_object = await reader.next()

        if task_metadata_object is None:  # weird error
            return web.Response(status=406)  # should have sent 3 parts
        task_metadata = await task_metadata_object.json()

        # Validate that the dictionary has these fields.
        if not validate_required_fields(
            task_metadata,
            [
                "user",
                "token",
                "comments",
                "pg",
                "ver",
                "score",
                "mtime",
                "tags",
                "md5sum",
                "integrity_check",
                "image_md5s",
            ],
        ):
            return web.Response(status=400)
        # Validate username and token.
        if not self.server.validate(task_metadata["user"], task_metadata["token"]):
            return web.Response(status=401)

        comments = task_metadata["comments"]  # List of comments.
        task_code = request.match_info["task"]  # Task code.

        # Note: if user isn't validated, we don't parse their binary junk
        # TODO: is it safe to abort during a multi-part thing?

        # Dealing with the image.
        task_image_object = await reader.next()

        if task_image_object is None:  # weird error
            return web.Response(status=406)  # should have sent 3 parts
        task_image = await task_image_object.read()

        # Dealing with the plom_file.
        plom_file_object = await reader.next()

        if plom_file_object is None:  # weird error
            return web.Response(status=406)  # should have sent 3 parts
        plomdat = await plom_file_object.read()

        marked_task_status = self.server.MreturnMarkedTask(
            task_metadata["user"],
            task_code,
            int(task_metadata["pg"]),
            int(task_metadata["ver"]),
            int(task_metadata["score"]),
            task_image,
            plomdat,
            comments,
            int(task_metadata["mtime"]),
            task_metadata["tags"],
            task_metadata["md5sum"],
            task_metadata["integrity_check"],
            task_metadata["image_md5s"],
        )
        # marked_task_status = either [True, Num Done tasks, Num Totalled tasks] or [False] if error.

        if marked_task_status[0]:
            num_done_tasks = marked_task_status[1]
            total_num_tasks = marked_task_status[2]
            return web.json_response([num_done_tasks, total_num_tasks], status=200)
        else:
            if marked_task_status[1] == "no_such_task":
                log.warning("Returning with error 410 = {}".format(marked_task_status))
                return web.Response(status=410)
            elif marked_task_status[1] == "not_owner":
                log.warning("Returning with error 409 = {}".format(marked_task_status))
                return web.Response(status=409)
            elif marked_task_status[1] == "integrity_fail":
                log.warning("Returning with error 406 = {}".format(marked_task_status))
                return web.Response(status=406)
            else:
                log.warning("Returning with error 400 = {}".format(marked_task_status))
                return web.Response(status=400)

    # @routes.get("/MK/images/{task}")
    @authenticate_by_token_required_fields(["user", "integrity_check"])
    def MgetImages(self, data, request):
        """Return underlying image data and annotations of a question/task.

        Main API call for the client to get the image data (original and annotated).
        Respond with status 200/409.

        Args:
            data (dict): A dictionary having the user/token.
            request (aiohttp.web_request.Request): Request of type GET /MK/images/"task code"
                which the task code is extracted from.

        Returns:
            aiohttp.web_response.Response: A response which includes the multipart writer object
                wrapping the task images.
        """

        task_code = request.match_info["task"]
        results = self.server.MgetImages(
            data["user"], task_code, data["integrity_check"]
        )
        # Format is one of:
        # [False, error]
        # [True, image_data]
        # [True, image_data, annotated_fname, plom_filename]
        if not results[0]:
            if results[1] == "owner":
                return web.Response(status=409)  # someone else has that task_image
            elif results[1] == "integrity_fail":
                return web.Response(status=406)  # task changed
            elif results[1] == "no_such_task":
                return web.Response(status=410)  # task deleted
            else:
                return web.Response(status=400)  # some other error

        with MultipartWriter("imageAnImageAndPlom") as multipart_writer:
            image_metadata = results[1]
            files = []
            # append the annotated_fname, plom_filename if present
            files.extend(results[2:])

            multipart_writer.append_json(image_metadata)
            for file_name in files:
                multipart_writer.append(open(file_name, "rb"))
        return web.Response(body=multipart_writer, status=200)

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
        task_code = request.match_info["task"]
        image_id = request.match_info["image_id"]
        md5sum = request.match_info["md5sum"]

        r = self.server.DB.MgetOneImageFilename(
            data["user"], task_code, image_id, md5sum
        )
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
        get_image_results = self.server.MgetOriginalImages(task)
        # returns either [True, md5s, fname1, fname2,... ] or [False]
        image_return_success = get_image_results[0]

        if not image_return_success:
            return web.Response(status=204)  # no content there

        original_image_paths = get_image_results[1:]
        with MultipartWriter("images") as multipart_writer:
            for file_nam in original_image_paths:
                multipart_writer.append(open(file_nam, "rb"))
        return web.Response(body=multipart_writer, status=200)

    # @routes.patch("/MK/tags/{task}")
    @authenticate_by_token_required_fields(["user", "tags"])
    def MsetTag(self, data, request):
        """Set tag for a task.

        Respond with status 200/409.

        Args:
            data (dict): A dictionary having the user/token in addition to the tag string.
                Request object also incudes the task code.
            request (aiohttp.web_request.Request): PATCH /MK/tags/`task_code` type request.

        Returns:
            aiohttp.web_response.Response: Empty status response indication is adding
                the tag was successful.
        """

        task_code = request.match_info["task"]
        set_tag_success = self.server.MsetTag(data["user"], task_code, data["tags"])

        if set_tag_success:
            return web.Response(status=200)
        else:
            return web.Response(status=409)  # Task does not belong to this user.

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

        with MultipartWriter("images") as multipart_writer:
            pages_data = whole_paper_response[1]
            all_pages_paths = whole_paper_response[2:]
            multipart_writer.append_json(pages_data)
            for file_name in all_pages_paths:
                multipart_writer.append(open(file_name, "rb"))
        return web.Response(body=multipart_writer, status=200)

    # @routes.get("/MK/TMP/whole/{number}/{question}")
    @authenticate_by_token_required_fields([])
    def MgetWholePaperMetadata(self, data, request):
        """Return the metadata for all images associated with a paper

        Respond with status 200/404.

        Args:
            data (dict): A dictionary having the user/token.
            request (aiohttp.web_request.Request): GET /MK/whole/`test_number`/`question_number`.

        Returns:
            aiohttp.web_response.Response: JSON data, a list of lists
                where each list in the form documented below.

        Each row of the data looks like:
           `[name, md5, true/false, pos_in_current_annotation, image_id]`
        """
        test_number = request.match_info["number"]
        # TODO: who cares about this?
        question_number = request.match_info["question"]

        # return [True, pageData, f1, f2, f3, ...] or [False]
        # 1. True/False for operation status.
        # 2. A list of lists, documented elsewhere (TODO: I hope)
        # 3. 3rd element onward: paths for each page of the paper in server.
        r = self.server.MgetWholePaper(test_number, question_number)

        if not r[0]:
            return web.Response(status=404)

        pages_data = r[1]
        # We just discard this, its legacy from previous API call
        # TODO: fold into the pages_data; then we can sanity check it when it comes back!
        all_pages_paths = r[2:]
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
        router.add_delete("/MK/tasks/{task}", self.MdidNotFinishTask)
        router.add_put("/MK/tasks/{task}", self.MreturnMarkedTask)
        router.add_get("/MK/images/{task}", self.MgetImages)
        router.add_get("/MK/images/{task}/{image_id}/{md5sum}", self.MgetOneImage)
        router.add_get("/MK/originalImages/{task}", self.MgetOriginalImages)
        router.add_patch("/MK/tags/{task}", self.MsetTag)
        router.add_get("/MK/whole/{number}/{question}", self.MgetWholePaper)
        router.add_get("/MK/TMP/whole/{number}/{question}", self.MgetWholePaperMetadata)
        router.add_patch("/MK/review", self.MreviewQuestion)
        router.add_patch("/MK/revert/{task}", self.MrevertTask)
