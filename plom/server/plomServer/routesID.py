# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2019-2020 Andrew Rechnitzer
# Copyright (C) 2020-2021 Colin B. Macdonald
# Copyright (C) 2020 Vala Vakilian

import csv
import os
from pathlib import Path

from aiohttp import web, MultipartWriter

from plom import specdir
from .routeutils import authenticate_by_token, authenticate_by_token_required_fields
from .routeutils import log

# I couldn't make this work with the auth deco
# routes = web.RouteTableDef()


class IDHandler:
    def __init__(self, plomServer):
        self.server = plomServer
        # self.local_route_table = routes

    # @routes.get("/ID/progress")
    @authenticate_by_token
    def IDprogressCount(self):
        """Send back current ID progress counts to the client.

        Responds with status 200.

        Returns:
            list: A list of [all the ID'd record , all the records] in the form of int.
        """
        return web.json_response(self.server.IDprogressCount(), status=200)

    # @routes.get("/ID/classlist")
    @authenticate_by_token
    def IDgetClasslist(self):
        """Returns the classlist to the client.

        Used, for example, to fill in the student details for the searchbar autofill.

        Responds with status success or HTTPNotFound.

        The classlist is a ordered list of (student ID, student name)
        pairs.

        Returns:
            class 'aiohttp.web_fileresponse.FileResponse: A file response that includes the classlist.
        """
        try:
            with open(Path(specdir) / "classlist.csv") as csvfile:
                reader = csv.reader(csvfile)
                next(reader)  # skip header row
                classlist = list(reader)
        except FileNotFoundError:
            raise web.HTTPNotFound(reason="classlist not found")
        return web.json_response(classlist)

    # @routes.put("/ID/classlist")
    @authenticate_by_token_required_fields(["user", "classlist"])
    def IDputClasslist(self, data, request):
        """Accept classlist upload.

        Only "manager" can perform this action.

        The classlist should be provided as a ordered list of (str, str)
        pairs where each pair is (student ID, student name).

        Side effects on the server test spec file:
          * If numberToName and/or numberToProduce are -1, values are
            set based on this classlist (spec is permanently altered)/
          * If numberToName < 0 but numberToProduce is too small for the
            result, respond with HTTPNotAcceptable.

        Returns:
            aiohttp.web_response.Response: Success or failure.  Can be:
                200: success
                400: authentication problem.
                HTTPBadRequest: not manager, or malformed request.
                HTTPConflict: we already have a classlist.
                    TODO: would be nice to be able to "try again".
                HTTPNotAcceptable: classlist too short (see above).
        """
        if not data["user"] == "manager":
            raise web.HTTPBadRequest(reason="Not manager")
        if os.path.isfile(Path(specdir) / "classlist.csv"):
            raise web.HTTPConflict(reason="we already have a classlist")
        classlist = data["classlist"]
        # TODO should we make copy until sure it passes verification?
        spec = self.server.testSpec
        if spec.numberToName < 0 or spec.numberToProduce < 0:
            if spec.number_to_name < 0:
                spec.set_number_papers_to_name(len(classlist))
            if spec.number_to_produce < 0:
                spec.set_number_papers_add_spares(len(classlist))
            try:
                spec.verifySpec(verbose="log")
            except ValueError as e:
                raise web.HTTPNotAcceptable(reason=str(e))
            spec.saveVerifiedSpec()
        with open(Path(specdir) / "classlist.csv", "w") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["id", "studentName"])
            writer.writerows(classlist)
        return web.Response()

    # @routes.get("/ID/predictions")
    @authenticate_by_token
    def IDgetPredictions(self):
        """Returns the files involving the ML model's student id's prediction.

        Responds with status 200/404.

        Returns:
            aiohttp.web_fileresponse.FileResponse: File response including the predictions.
        """
        if os.path.isfile(Path(specdir) / "predictionlist.csv"):
            return web.FileResponse(Path(specdir) / "predictionlist.csv", status=200)
        else:
            return web.Response(status=404)

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
                Each list in the response is of the format: [task_number, task_status, student_id, student_name]
        """

        # return the completed list
        return web.json_response(self.server.IDgetDoneTasks(data["user"]), status=200)

    # @routes.get("/ID/images/{test}")
    @authenticate_by_token_required_fields(["user"])
    def IDgetImage(self, data, request):
        """Return the images for a specified paper number.

        Responds with status 200/404/409/410.

        Args:
            data (dict): A (str:str) dictionary having keys `user` and `token`.
            request (aiohttp.web_request.Request): DELETE /ID/predictedID type request object.

        Returns:
            aiohttp.web_fileresponse.FileResponse: A response including a aiohttp object which
                includes a multipart object with the images.
        """

        # A string having the sting number.
        test_number = request.match_info["test"]

        image_path = self.server.IDgetImage(data["user"], test_number)
        # is either user allowed access - returns [true, fname0, fname1,...]
        # or fails - return [false, message]

        allow_access = image_path[0]
        if not allow_access:
            # can fail for 3 reasons - "not owner", "no such scan", "no such test"
            fail_message = image_path[1]
            if fail_message == "NotOwner":
                return web.Response(status=409)  # someone else has that image
            elif fail_message == "NoScan":
                return web.Response(status=410)
            else:  # fail_message == "NoTest":
                return web.Response(status=404)

        with MultipartWriter("images") as writer:
            image_paths = image_path[1:]

            for file_name in image_paths:
                if os.path.isfile(file_name):
                    writer.append(open(file_name, "rb"))
                else:
                    return web.Response(status=404)
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

        next_task_code = self.server.IDgetNextTask()  # returns [True, code] or [False]
        next_task_available = next_task_code[0]

        if next_task_available:
            next_task_code = next_task_code[1]
            return web.json_response(next_task_code, status=200)
        else:
            return web.Response(status=204)  # no papers left

    # @routes.patch("/ID/tasks/{task}")
    @authenticate_by_token_required_fields(["user"])
    def IDclaimThisTask(self, data, request):
        """Claims this identifying task and returns images of the ID pages.

        Responds with status 200/204/404.

        Args:
            data (dict): A (str:str) dictionary having keys `user` and `token`.
            request (aiohttp.web_request.Request): PATCH /ID/tasks request object.

        Returns:
            aiohttp.web_response.Response: A response including a aiohttp object which
                includes a multipart object with the images.
        """

        testNumber = request.match_info["task"]
        image_path = self.server.IDclaimThisTask(
            data["user"], testNumber
        )  # returns [True, IMG_path] or [False]

        allow_access = image_path[0]

        if allow_access:  # user allowed access - returns [true, fname0, fname1,...]
            with MultipartWriter("images") as writer:
                image_paths = image_path[1:]

                for file_name in image_paths:
                    if os.path.isfile(file_name):
                        writer.append(open(file_name, "rb"))
                    else:
                        return web.Response(status=404)
                return web.Response(body=writer, status=200)
        else:
            return web.Response(status=204)  # that task already taken.

    # @routes.put("/ID/tasks/{task}")
    @authenticate_by_token_required_fields(["user", "sid", "sname"])
    def IdentifyPaperTask(self, data, request):
        """Identify a paper based on a task.

        Returns:
            403: some other user owns this task.
            404: papernum not found, or other data errors.
            409: student number `data["sid"]` is already in use.
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
            # catch all that should not happen.
            raise web.HTTPInternalServerError(reason=msg)

    # @routes.put("/ID/{papernum}")
    @authenticate_by_token_required_fields(["user", "sid", "sname"])
    def IdentifyPaper(self, data, request):
        """Identify a paper directly without certain checks.

        Only "manager" can perform this action.  Typical client IDing
        would call func:`IdentifyPaperTask` instead.

        Returns:
            400: not manager.
            404: papernum not found, or other data errors.
            409: student number `data["sid"]` is already in use.
        """
        if not data["user"] == "manager":
            raise web.HTTPBadRequest(reason="Not manager")
        papernum = request.match_info["papernum"]
        r, what, msg = self.server.id_paper(papernum, "HAL", data["sid"], data["sname"])
        if r:
            return web.Response(status=200)
        elif what == 409:
            raise web.HTTPConflict(reason=msg)
        elif what == 404:
            raise web.HTTPNotFound(reason=msg)
        else:
            # catch all that should not happen.
            raise web.HTTPInternalServerError(reason=msg)

    # @routes.delete("/ID/tasks/{task}")
    @authenticate_by_token_required_fields(["user"])
    def IDdidNotFinishTask(self, data, request):
        """Accept the client's surrender of a previously-claimed identifying task.

        This could occur for example when the client closes with unfinished tasks.
        Responds with status 200.

        Args:
            data (dict): A (str:str) dictionary having keys `user` and `token`.
            request (aiohttp.web_request.Request'): Request of type DELETE /ID/tasks/#TaskNumber.

        Returns:
            aiohttp.web_response.Response: A response with status 200.
        """

        testNumber = request.match_info["task"]
        self.server.IDdidNotFinish(data["user"], testNumber)
        return web.json_response(status=200)

    # @routes.get("/ID/randomImage")
    @authenticate_by_token_required_fields(["user"])
    def IDgetImageFromATest(self, data, request):
        """Gets a random image to extract the bounding box corresponding to the student name and id.

        The bounding box indicated on this image will be later used to extract the
        student ids from the other papers.
        Responds with status 200/404/410.
        Logs activity.

        Args:
            data (dict): A (str:str) dictionary having keys `user` and `token`.
            request (aiohttp.web_request.Request): request of type GET /ID/randomImage.
        Returns:
            aiohttp.web_fileresponse.FileResponse: A response including a aiohttp object which
                includes a multipart object with the images.
        """

        # TODO: maybe we want some special message here?
        if data["user"] != "manager":
            return web.Response(status=401)  # only manager

        # A list with a boolean (indicating wether the objects exist) and a list of the exam images.
        random_image_paths = self.server.IDgetImageFromATest()

        allow_access = random_image_paths[0]

        # No access to the files
        if allow_access is False:
            return web.Response(status=410)

        log.debug("Appending file {}".format(random_image_paths))
        with MultipartWriter("images") as writer:
            image_paths = random_image_paths[1:]

            for file_name in image_paths:
                if os.path.isfile(file_name):
                    writer.append(open(file_name, "rb"))
                else:
                    return web.Response(status=404)
            return web.Response(body=writer, status=200)

    @authenticate_by_token_required_fields(["user"])
    def IDdeletePredictions(self, data, request):
        """Deletes the machine-learning predicted IDs for all papers.

        Responds with status 200/401.

        Args:
            data (dict): A (str:str) dictionary having keys `user` and `token`.
            request (aiohttp.web_request.Request): DELETE /ID/predictedID type request object.

        Returns:
            aiohttp.web_response.Response: Returns a response with a True or False indicating if the deletion
                was successful.
        """

        # TODO: maybe we want some special message here?
        if data["user"] != "manager":
            return web.Response(status=401)

        return web.json_response(self.server.IDdeletePredictions(), status=200)

    @authenticate_by_token_required_fields(
        ["user", "rectangle", "fileNumber", "ignoreStamp"]
    )
    def IDrunPredictions(self, data, request):
        """Runs the id prediction on all paper images.

        Responds with status 200/202/205/401.

        Args:
            data (dict): A dictionary having the user/token in addition to information from the rectangle
                bounding box coordinates and file information.
            request (aiohttp.web_request.Request): Request of type POST /ID/predictedID.

        Returns:
            aiohttp.web_response.Response: Returns a response with the date and time of the prediction run.
                Or responds with saying the prediction is already running.
        """

        # TODO: maybe we want some special message here?
        if data["user"] != "manager":
            return web.Response(status=401)

        prediction_results = self.server.IDrunPredictions(
            data["rectangle"], data["fileNumber"], data["ignoreStamp"]
        )

        timestamp_found = prediction_results[0]
        is_running = prediction_results[1]

        if timestamp_found:  # set running or is running
            if is_running:
                return web.Response(status=200)
            else:
                return web.Response(status=202)  # is already running
        else:  # isn't running because we found a time-stamp
            return web.Response(text=is_running, status=205)

    # @routes.patch("/ID/review")
    @authenticate_by_token_required_fields(["testNumber"])
    def IDreviewID(self, data, request):
        """Responds with an empty response object indicating if the review ID is possible and the document exists.

        Responds with status 200/404.

        Args:
            data (dict): A dictionary having the user/token in addition to the `testNumber`.
            request (aiohttp.web_request.Request): Request of type PATCH /ID/review.

        Returns:
            aiohttp.web_fileresponse.FileResponse: An empty response indicating the availability status of
                the review document.
        """

        if self.server.IDreviewID(data["testNumber"]):
            return web.Response(status=200)
        else:
            return web.Response(status=404)

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
        router.add_get("/ID/tasks/complete", self.IDgetDoneTasks)
        router.add_get("/ID/images/{test}", self.IDgetImage)
        router.add_get("/ID/tasks/available", self.IDgetNextTask)
        router.add_patch("/ID/tasks/{task}", self.IDclaimThisTask)
        router.add_put("/ID/{papernum}", self.IdentifyPaper)
        router.add_put("/ID/tasks/{task}", self.IdentifyPaperTask)
        router.add_delete("/ID/tasks/{task}", self.IDdidNotFinishTask)
        router.add_get("/ID/randomImage", self.IDgetImageFromATest)
        router.add_delete("/ID/predictedID", self.IDdeletePredictions)
        router.add_post("/ID/predictedID", self.IDrunPredictions)
        router.add_patch("/ID/review", self.IDreviewID)
