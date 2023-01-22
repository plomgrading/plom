# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2019-2021 Andrew Rechnitzer
# Copyright (C) 2020-2023 Colin B. Macdonald
# Copyright (C) 2020 Vala Vakilian
# Copyright (C) 2022 Natalie Balashov

import csv
import os

from aiohttp import web, MultipartWriter

from plom import specdir
from .routeutils import authenticate_by_token, authenticate_by_token_required_fields
from .routeutils import readonly_admin, write_admin
from .routeutils import log

# I couldn't make this work with the auth deco
# routes = web.RouteTableDef()


class IDHandler:
    """The ID Handler interfaces between the HTTP API and the server itself.

    These routes handle requests related to identifying papers.
    """

    def __init__(self, plomServer):
        self.server = plomServer
        # self.local_route_table = routes

    # @routes.get("/ID/progress")
    @authenticate_by_token
    def IDprogressCount(self):
        """Send back current ID progress counts to the client.

        Responds with status 200.

        Returns:
            list: A list of [all the ID'd records, all the records] in the form of ints.
        """
        return web.json_response(self.server.IDprogressCount(), status=200)

    # @routes.get("/ID/classlist")
    @authenticate_by_token
    def IDgetClasslist(self):
        """Returns the classlist to the client.

        The classlist is an ordered list of dicts where each row has
        at least the primary key `"id"` and `"name"` and `"paper_number"`.
        It may contain other keys.

        Used, for example, to fill in the student details for the searchbar autofill.

        Responds with status success or HTTPNotFound.

        Returns:
            aiohttp.json_response: list of dicts as above.
        """
        try:
            with open(specdir / "classlist.csv", "r") as f:
                reader = csv.DictReader(f)
                classlist = list(reader)
        except FileNotFoundError:
            raise web.HTTPNotFound(reason="classlist not found")
        return web.json_response(classlist)

    # @routes.put("/ID/classlist")
    @authenticate_by_token_required_fields(["user", "classlist", "force"])
    @write_admin
    def IDputClasslist(self, data, request):
        """Accept classlist upload.

        Only "manager" can perform this action.

        The classlist should be provided as list of dicts.  Each row
        must contain `"id"` and `"studentNumber"` keys (case matters).
        Currently `id` must be a UBC-style student number, although it
        is anticipated this restriction will be removed in favour of
        an agnostic key.  There can be other keys which should be
        homogeneous between rows (TODO: not well-specified what happens
        if not).  These other fields will be given back if you get the
        classlist later.

        Side effects on the server test spec file:

        * If numberToProduce is -1, value is set based on
          this classlist (spec is permanently altered).

        If data["force"] is True, then you can push a new classlist.
        This is not supported.  Somethings to be aware of:

        * if you previously used numberToProduce of -1 and then
          pushed a classlist of length 100, then numberToProduce
          is now 100.  If you force push a classlist of a different
          size, you may not have enough papers.
        * If you have produced prenamed papers then those predictions
          may not appear in the new classlist; nothing good will come
          from this.

        Returns:
            aiohttp.web_response.Response: Success or failure.  Can be:

            - 200: success.
            - 401: authentication problem.
            - 403: not manager.
            - HTTPBadRequest (400): malformed request such as missing
              required fields or server has no spec.
            - HTTPConflict: we already have a classlist, and `force`
              was False (the default).
            - HTTPNotAcceptable: classlist too short (see above).
        """
        spec = self.server.testSpec
        if not spec:
            raise web.HTTPBadRequest(
                reason="Server has no spec; cannot accept classlist"
            )
        force = data.get("force", False)
        if (specdir / "classlist.csv").exists() and not force:
            raise web.HTTPConflict(reason="we already have a classlist")
        classlist = data["classlist"]

        # TODO - these checks should likely go into a serverBlah.py

        # verify classlist: all rows must have non-empty ID
        for row in classlist:
            if "id" not in row:
                raise web.HTTPBadRequest(reason="Every row must have an id")
            if not row["id"]:
                raise web.HTTPBadRequest(reason="Every row must non-empty id")

        if spec.numberToProduce < 0:
            spec.set_number_papers_add_spares(len(classlist))
            try:
                spec.verifySpec(verbose="log")
            except ValueError as e:
                raise web.HTTPNotAcceptable(reason=str(e))
            spec.saveVerifiedSpec()
        # these keys first...
        fieldnames = ["id", "name", "paper_number"]
        # then all the others in any order
        fieldnames.extend(set(classlist[0].keys()) - set(fieldnames))
        log.info(f"Classlist upload w/ fieldnames {fieldnames}")
        missing = ""
        with open(specdir / "classlist.csv", "w") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, restval=missing)
            writer.writeheader()
            try:
                writer.writerows(classlist)
            except ValueError as e:
                raise web.HTTPBadRequest(
                    reason=f'Extra field in row "{row}". Error: "{e}"'
                )
        return web.Response()

    # @routes.get("/ID/predictions")
    @authenticate_by_token
    def IDgetPredictions(self):
        """Returns all predictions for the identification of each paper.

        Each entry in the dict may contain multiple predictions.

        Returns:
            aiohttp.web_json_response: on success a dict where keys are
            str of papernum, values are lists of dicts with keys
            `"student_id"`, `"certainty"`, and `"predictor"`.
            Can fail with 400 (malformed) or 401 (auth trouble).
        """
        return web.json_response(self.server.ID_get_predictions())

    # @routes.get("/ID/predictions/{predictor}")
    @authenticate_by_token_required_fields([])
    def IDgetPredictionsFromPredictor(self, data, request):
        """Returns predictions from a particular predictor for the identification.

        Returns:
            aiohttp.web_json_response: on success a dict where keys are
            str of papernum, values themselves dicts with keys
            `"student_id"`, `"certainty"`, and `"predictor"`.
            The `"predictor"` field is probably redundant: its what you
            asked for parroted back to you.
            Can fail with 400 (malformed) or 401 (auth trouble).
        """
        predictor = request.match_info["predictor"]
        return web.json_response(self.server.ID_get_predictions(predictor=predictor))

    # @routes.delete("/ID/predictions")
    @authenticate_by_token_required_fields([])
    @write_admin
    def ID_delete_all_predictions(self, data, request):
        """Removes all predictions from all predictors for the identification.

        Returns:
            200 on success.
            Can fail with 400 (malformed) or 401/403 (auth trouble).
        """
        self.server.ID_delete_predictions()
        return web.Response()

    # @routes.delete("/ID/predictions/{predictor}")
    @authenticate_by_token_required_fields([])
    @write_admin
    def ID_delete_predictions_from_predictor(self, data, request):
        """Removes all predictions from a particular predictor for the identification.

        Returns:
            200 on success.
            Can fail with 400 (malformed) or 401/403 (auth trouble).
        """
        predictor = request.match_info["predictor"]
        self.server.ID_delete_predictions(predictor=predictor)
        return web.Response()

    # @routes.get("/ID/tasks/complete")
    @authenticate_by_token_required_fields(["user"])
    def IDgetDoneTasks(self, data, request):
        """Responds with a list of id/name which have already been confirmed by the client.

        Args:
            data (dict): A (str:str) dictionary having keys `user` and `token`.
            request (aiohttp.web_request.Request): GET /ID/tasks/complete  request type.

        Returns:
            aiohttp.web_request.Request: A response including a list of lists indicating information about
            the users who already have confirmed predictions.
            Each list in the response is of the format: `[task_number, task_status, student_id, student_name]`.
        """

        # return the completed list
        return web.json_response(self.server.IDgetDoneTasks(data["user"]), status=200)

    # @routes.get("/ID/image/{test}")
    @authenticate_by_token_required_fields(["user"])
    def IDgetImage(self, data, request):
        """Return the ID page image for a specified paper number.

        Responds with status 200/204/404/409/410.

        Args:
            data (dict): A (str:str) dictionary having keys `user` and `token`.
            request (aiohttp.web_request.Request):

        Returns:
            aiohttp.web_response.Response: If successful, then either
            status 200 is returned with a (positive length) multipart
            object of the images, or status 204 is returned when no
            images. Unsuccessful return values include:

            - HTTPBadRequest: authentication problem.
            - HTTPNotFound (404): no such paper.
            - HTTPConflict (409): not the owner, or not manager, and
              someone else has the image
            - HTTPGone (410): the paper is not scanned *and* has not been ID'd.

        .. note:: if the paper is not fully scanned---specifically
                        if the ID pages are not scanned but nonetheless the
                        paper is identified, then you won't get 410, but rather 204.
                        This is required to handle the case of HW uploads in which
                        we know the student associated with the paper but there are
                        no ID-pages (and so the associated ID group is unscanned).
        """
        test_number = request.match_info["test"]

        status, output = self.server.IDgetImage(data["user"], test_number)

        if not status:
            if output == "NotOwner":
                raise web.HTTPConflict(reason="Not owner, someone else has that image")
            elif output == "NoScanAndNotIDd":
                raise web.HTTPGone(
                    reason=f"Paper {test_number} has not been ID'd and the ID-pages have not been scanned"
                )
            else:  # output == "NoTest":
                raise web.HTTPNotFound(reason=f"No such paper number {test_number}")

        # if there are no such files return a success but with code 204 = no content.
        if not output:
            return web.Response(status=204)
        else:
            return web.FileResponse(output, status=200)

    # @routes.get("/ID/donotmark_images/{test}")
    @authenticate_by_token_required_fields([])
    def ID_get_donotmark_images(self, data, request):
        """Return the Do Not Mark page images for a specified paper number.

        Responds with status 200/204/404/410.

        Args:
            data (dict): A (str:str) dictionary having keys `user` and `token`.
            request (aiohttp.web_request.Request):

        Returns:
            aiohttp.web_response.Response: If successful, then either
            status 200 is returned with a (positive length) multipart
            object of the images, or status 204 is returned when no
            images. Unsuccessful return values include:

            - HTTPBadRequest: authentication problem.
            - HTTPNotFound (404): no such paper.
            - HTTPGone (410): the paper is not scanned *and* has not been ID'd.

        .. note:: if the paper is not fully scanned---specifically
                        if the DNM pages are not scanned but nonetheless the
                        paper is identified, then you won't get 410, but rather 204.
                        This is required to handle the case of HW uploads in which
                        we know the student associated with the paper but there are
                        no DNM-pages (and so the associated DNM group is unscanned).
        """
        test_number = request.match_info["test"]

        status, output = self.server.ID_get_donotmark_images(test_number)

        if not status:
            if output == "NoScanAndNotIDd":
                return web.Response(status=410)
            else:  # fail_message == "NoTest":
                return web.Response(status=404)

        # if there are no such files return a success but with code 204 = no content.
        if len(output) == 0:
            return web.Response(status=204)

        with MultipartWriter("images") as writer:
            for file_name in output:
                try:
                    with open(file_name, "rb") as fh:
                        raw_bytes = fh.read()
                except OSError as e:  # file not found, permission, etc
                    raise web.HTTPInternalServerError(
                        reason=f"Problem reading image: {e}"
                    )
                writer.append(raw_bytes)
            return web.Response(body=writer, status=200)

    # @routes.get("/ID/tasks/available")
    @authenticate_by_token
    def IDgetNextTask(self):
        """Responds with a code for the the next available identify task.

        Note: There is no guarantee that task will still be available later but at this moment in time,
        no one else has claimed it

        Responds with status 200/204.

        Returns:
            aiohttp.web_response.Response: A response object with the code for the next task/paper.
        """
        next_task_code = self.server.IDgetNextTask()
        if next_task_code is None:
            return web.Response(status=204)  # no papers left
        return web.json_response(next_task_code, status=200)

    # @routes.patch("/ID/tasks/{task}")
    @authenticate_by_token_required_fields(["user"])
    def IDclaimThisTask(self, data, request):
        """Claims this identifying task for the user.

        Args:
            data (dict): A (str:str) dictionary having keys `user` and `token`.
            request (aiohttp.web_request.Request): PATCH /ID/tasks request object.

        Returns:
            aiohttp.web_response.Response: Success or failure.  Can be:

            - 200: success, you have claimed the task.
            - 401: authentication problem.
            - 409: someone else claimed it before you.
            - 404/410: no such paper or not scanned.
        """
        testNumber = request.match_info["task"]
        status, output = self.server.IDclaimThisTask(data["user"], testNumber)
        if status:
            return web.Response(status=200)
        if output == "NotOwner":
            raise web.HTTPConflict(reason="Someone else took the task before you")
        if output == "NotScanned":
            raise web.HTTPGone(reason="Paper (or at least ID page) not yet scanned")
        if output == "NoTest":
            raise web.HTTPNotFound(reason="No such paper")
        raise web.HTTPBadRequest(reason=f'Unexpected database response: "{output}"')

    # @routes.put("/ID/tasks/{task}")
    @authenticate_by_token_required_fields(["user", "sid", "sname"])
    def IdentifyPaperTask(self, data, request):
        """Identify a paper based on a task.

        Returns:
            aiohttp.web_response.Response: Success or failure.  Can be:

            - 200: success.
            - 403: some other user owns this task.
            - 404: papernum not found, or other data errors.
            - 409: student number `data["sid"]` is already in use.
        """
        papernum = request.match_info["task"]
        r, what, msg = self.server.ID_id_paper(
            papernum, data["user"], data["sid"], data["sname"]
        )
        if r:
            return web.Response(status=200)
        elif what == 409:
            raise web.HTTPConflict(reason=msg)
        elif what == 404:
            raise web.HTTPNotFound(reason=msg)
        elif what == 403:
            raise web.HTTPForbidden(reason=msg)
        else:
            raise web.HTTPInternalServerError(reason=msg)

    # @routes.put("/ID/{papernum}")
    @authenticate_by_token_required_fields(["user", "sid", "sname"])
    @write_admin
    def IdentifyPaper(self, data, request):
        """Identify a paper directly without certain checks.

        Only "manager" can perform this action.  Typical client IDing
        would call :func:`IdentifyPaperTask` instead.

        Returns:
            aiohttp.web_response.Response: Success or failure.  Can be:

            - 200: success.
            - 403: not manager.
            - 404: papernum not found, or other data errors.
            - 409: student number `data["sid"]` is already in use.
        """
        papernum = request.match_info["paper_number"]

        r, what, msg = self.server.ID_id_paper(
            papernum, "HAL", data["sid"], data["sname"], checks=False
        )
        if r:
            return web.Response(status=200)
        elif what == 409:
            raise web.HTTPConflict(reason=msg)
        elif what == 404:
            raise web.HTTPNotFound(reason=msg)
        else:
            raise web.HTTPInternalServerError(reason=msg)

    # @routes.deletet("/ID/{paper_number}")
    @authenticate_by_token_required_fields([])
    @write_admin
    def un_id_paper(self, data, request):
        paper_number = request.match_info["paper_number"]
        if self.server.DB.remove_id_from_paper(paper_number):
            return web.Response(status=200)
        raise web.HTTPNotAcceptable(reason=f"Did not find papernum {paper_number}")

    # @routes.put("/ID/preid/{paper_number}")
    @authenticate_by_token_required_fields(["user", "sid", "certainty", "predictor"])
    @write_admin
    def pre_id_paper(self, data, request):
        """Set the prediction identification for a paper.

        Returns:
            aiohttp.web_response.Response: Success or failure.  Can be:

            - 200: success.
            - 401: auth
            - 403: not manager.
            - 404: papernum not found, or other data errors.
        """
        papernum = request.match_info["paper_number"]
        r, what, msg = self.server.add_or_change_predicted_id(
            papernum,
            data["sid"],
            certainty=data["certainty"],
            predictor=data["predictor"],
        )
        if r:
            return web.Response(status=200)
        elif what == 404:
            raise web.HTTPNotFound(reason=msg)
        raise web.HTTPInternalServerError(reason=msg)

    # @routes.delete("/ID/preid/{paper_number}")
    @authenticate_by_token_required_fields([])
    @write_admin
    def remove_pre_id(self, data, request):
        """Remove the "prename" prediction identification for a paper.

        Only "manager" can perform this action.  Typical client IDing
        would call func:`IdentifyPaperTask` instead.

        Returns:
            aiohttp.web_response.Response: Success or failure.  Can be:

            - 200: success.
            - 403: not manager.
            - 404: papernum not found, or other data errors.
        """
        papernum = request.match_info["paper_number"]
        r, what, msg = self.server.remove_predicted_id(papernum, predictor="prename")
        if r:
            return web.Response(status=200)
        elif what == 404:
            raise web.HTTPNotFound(reason=msg)
        else:
            raise web.HTTPInternalServerError(reason=msg)

    # @routes.get("/ID/randomImage")
    @authenticate_by_token_required_fields(["user"])
    @readonly_admin
    def IDgetImageFromATest(self, data, request):
        """Gets a random image to extract the bounding box corresponding to the student name and id.

        The bounding box indicated on this image will be later used to extract the
        student ids from the other papers.
        Responds with status 200/401/403/404/410.
        Logs activity.

        Args:
            data (dict): A (str:str) dictionary having keys `user` and `token`.
            request (aiohttp.web_request.Request): request of type GET /ID/randomImage.

        Returns:
            aiohttp.web_fileresponse.FileResponse: A response including a aiohttp object which
            includes a multipart object with the images.
        """
        # A list with a boolean (indicating whether the objects exist) and a list of the exam images.
        random_image_paths = self.server.IDgetImageFromATest()

        allow_access = random_image_paths[0]

        # No access to the files
        if allow_access is False:
            return web.Response(status=410)

        image_paths = random_image_paths[1:]
        log.debug("Appending files {}".format(image_paths))
        with MultipartWriter("images") as writer:
            for file_name in image_paths:
                if not os.path.isfile(file_name):
                    return web.Response(status=404)
                with open(file_name, "rb") as fh:
                    raw_bytes = fh.read()
                writer.append(raw_bytes)
            return web.Response(body=writer, status=200)

    # @routes.delete("/ID/predictedID")
    @authenticate_by_token_required_fields(["user"])
    @write_admin
    def ID_delete_machine_predictions(self, data, request):
        """Deletes the machine-learning predicted IDs for all papers.

        Args:
            data (dict): A (str:str) dictionary having keys `user` and `token`.
            request (aiohttp.web_request.Request):

        Returns:
            aiohttp.web_response.Response: 200 if successful.
            400 for malformed, or 401/403 for auth trouble.
        """
        self.server.ID_delete_predictions(predictor="MLLAP")
        self.server.ID_delete_predictions(predictor="MLGreedy")
        return web.Response(status=200)

    # @routes.get("/ID/id_reader"
    @authenticate_by_token_required_fields([])
    @write_admin
    def id_reader_get_log(self, data, request):
        is_running, time_stamp, partial_log = self.server.id_reader_get_log()
        return web.json_response([is_running, time_stamp, partial_log], status=200)

    # @routes.post("/ID/id_reader")
    @authenticate_by_token_required_fields(
        ["user", "crop_top", "crop_bottom", "ignore_timestamp"]
    )
    @write_admin
    def id_reader_run(self, data, request):
        """Runs the id digit reader on all paper ID pages.

        Responds with status 200/202/205/401/403.

        Args:
            data (dict): A dictionary having the user/token, cropping info
                and flag to ignore time stamp.
            request (aiohttp.web_request.Request): Request of type POST /ID/predictedID.

        Returns:
            aiohttp.web_response.Response: Returns a response with the date and time of the machine reader run.
            Or responds with saying the machine reader is already running.
        """
        is_running, new_start, time_stamp = self.server.id_reader_run(
            data["crop_top"],
            data["crop_bottom"],
            ignore_timestamp=data["ignore_timestamp"],
        )
        if is_running:
            if new_start:
                return web.json_response([time_stamp], status=200)
            else:  # ... or one was already running
                return web.json_response([time_stamp], status=202)
        else:
            return web.json_response([time_stamp], status=205)

    # @routes.delete("/ID/id_reader")
    @authenticate_by_token_required_fields([])
    @write_admin
    def id_reader_kill(self, data, request):
        ok, msg = self.server.id_reader_kill()
        # TODO not ok?  or remove this feature?
        return web.json_response(msg, status=200)

    @authenticate_by_token_required_fields(["user"])
    @write_admin
    def machine_learning_predict_id(self, data, request):
        """Match Runs the id digit reader (MLLAP and MLGreedy) on all paper ID pages.

        Args:
            data (dict): A dictionary having the user/token.
            request (aiohttp.web_request.Request):

        Returns:
            aiohttp.web_response.Response: Can be:

            - 200: successful, with some status text explaing what happened.
            - 401/403: authentication troubles
            - 406 (not acceptable): LAP is degenerate
            - 409 (conflict): ID reader still running
            - 412 (precondition failed) for no ID reader
        """
        try:
            status = self.server.predict_id_lap_solver()
            status += "\n"
            status += self.server.predict_id_greedy()
        except RuntimeError as e:
            log.warning(e)
            return web.HTTPConflict(reason=e)
        except IndexError as e:
            log.warning(e)
            return web.HTTPNotAcceptable(reason=e)
        except FileNotFoundError as e:
            log.warning(e)
            return web.HTTPPreconditionFailed(reason=f"Must run id reader first: {e}")
        return web.Response(text=status, status=200)

    # @routes.patch("/ID/review")
    @authenticate_by_token_required_fields(["testNumber"])
    @write_admin
    def IDreviewID(self, data, request):
        """Responds with an empty response object indicating if the review ID is possible and the document exists.

        Responds with status 200/404.

        Args:
            data (dict): A dictionary having the user/token in addition to the `testNumber`.
            request (aiohttp.web_request.Request): Request of type PATCH /ID/review.

        Returns:
            aiohttp.web.Response: 200 on success, 404 on failure (could not find).
        """
        if not self.server.IDreviewID(data["testNumber"]):
            raise web.HTTPNotFound(reason=f'Could not find paper {data["testNumber"]}')
        return web.Response(status=200)

    def setUpRoutes(self, router):
        """Adds the response functions to the router object.

        Args:
            router (aiohttp.web_urldispatcher.UrlDispatcher): Router object which we will add the response functions to.
        """

        # router.add_routes(self.local_route_table)
        # But see above: doesn't work with auth deco
        router.add_get("/ID/progress", self.IDprogressCount)
        router.add_get("/ID/classlist", self.IDgetClasslist)
        router.add_put("/ID/classlist", self.IDputClasslist)
        router.add_get("/ID/predictions", self.IDgetPredictions)
        router.add_delete("/ID/predictions", self.ID_delete_all_predictions)
        router.add_get(
            "/ID/predictions/{predictor}", self.IDgetPredictionsFromPredictor
        )
        router.add_delete(
            "/ID/predictions/{predictor}", self.ID_delete_predictions_from_predictor
        )
        router.add_get("/ID/tasks/complete", self.IDgetDoneTasks)
        router.add_get("/ID/image/{test}", self.IDgetImage)
        router.add_get("/ID/donotmark_images/{test}", self.ID_get_donotmark_images)
        router.add_get("/ID/tasks/available", self.IDgetNextTask)
        router.add_patch("/ID/tasks/{task}", self.IDclaimThisTask)
        router.add_put("/ID/tasks/{task}", self.IdentifyPaperTask)
        router.add_put("/ID/preid/{paper_number}", self.pre_id_paper)
        router.add_delete("/ID/preid/{paper_number}", self.remove_pre_id)
        router.add_get("/ID/randomImage", self.IDgetImageFromATest)
        # TODO: likely unnecessary?
        router.add_delete("/ID/predictedID", self.ID_delete_machine_predictions)
        router.add_post("/ID/predictedID", self.machine_learning_predict_id)
        router.add_get("/ID/id_reader", self.id_reader_get_log)
        router.add_post("/ID/id_reader", self.id_reader_run)
        router.add_delete("/ID/id_reader", self.id_reader_kill)
        router.add_patch("/ID/review", self.IDreviewID)
        # careful, list these last as they can glob other URLs
        router.add_put("/ID/{paper_number}", self.IdentifyPaper)
        router.add_delete("/ID/{paper_number}", self.un_id_paper)
