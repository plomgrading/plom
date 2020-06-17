# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2019-2020 Andrew Rechnitzer
# Copyright (C) 2020 Colin B. Macdonald

import csv
import os
from pathlib import Path

from aiohttp import web, MultipartWriter, MultipartReader

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
        return web.json_response(self.server.IDprogressCount(), status=200)

    # @routes.get("/ID/classlist")
    @authenticate_by_token
    def IDgetClasslist(self):
        """Return the classlist.

        Returns:
            200: the classlist dict.
            404: there is no classlist.
        """
        try:
            with open(Path(specdir) / "classlist.csv") as csvfile:
                reader = csv.reader(csvfile)
                next(reader)  # skip header row
                cl = dict(reader)
        except FileNotFoundError:
            raise web.HTTPNotFound(reason="classlist not found")
        return web.json_response(cl)

    # @routes.put("/ID/classlist")
    @authenticate_by_token_required_fields(["user", "classlist"])
    def IDputClasslist(self, data, request):
        """Accept classlist upload.

        Only "manager" can perform this action.

        Returns:
            400: not manager
            409: we already have one.  TODO: try again with force.
        """
        if not data["user"] == "manager":
            raise web.HTTPBadRequest(reason="Not manager")
        cl = data["classlist"]
        if os.path.isfile(Path(specdir) / "classlist.csv"):
            raise web.HTTPConflict(reason="we already have a classlist")
        with open(Path(specdir) / "classlist.csv", "w") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["id", "studentName"])
            writer.writerows(cl.items())
        return web.Response()

    # @routes.get("/ID/predictions")
    @authenticate_by_token
    def IDgetPredictions(self):
        if os.path.isfile(Path(specdir) / "predictionlist.csv"):
            return web.FileResponse(Path(specdir) / "predictionlist.csv", status=200)
        else:
            return web.Response(status=404)

    # @routes.get("/ID/tasks/complete")
    @authenticate_by_token_required_fields(["user"])
    def IDgetDoneTasks(self, data, request):
        # return the completed list
        return web.json_response(self.server.IDgetDoneTasks(data["user"]), status=200)

    # @routes.get("/ID/images/{test}")
    @authenticate_by_token_required_fields(["user"])
    def IDgetImage(self, data, request):
        test = request.match_info["test"]
        rmsg = self.server.IDgetImage(data["user"], test)
        if not rmsg[0]:  # user allowed access - returns [true, fname0, fname1,...]
            return web.Response(status=409)  # someone else has that image
        with MultipartWriter("images") as mpwriter:
            for fn in rmsg[1:]:
                if os.path.isfile(fn):
                    mpwriter.append(open(fn, "rb"))
                else:
                    return web.Response(status=404)
            return web.Response(body=mpwriter, status=200)

    # @routes.get("/ID/tasks/available")
    @authenticate_by_token
    def IDgetNextTask(self):
        rmsg = self.server.IDgetNextTask()  # returns [True, code] or [False]
        if rmsg[0]:
            return web.json_response(rmsg[1], status=200)
        else:
            return web.Response(status=204)  # no papers left

    # @routes.patch("/ID/tasks/{task}")
    @authenticate_by_token_required_fields(["user"])
    def IDclaimThisTask(self, data, request):
        testNumber = request.match_info["task"]
        rmsg = self.server.IDclaimThisTask(data["user"], testNumber)
        if rmsg[0]:  # user allowed access - returns [true, fname0, fname1,...]
            with MultipartWriter("images") as mpwriter:
                for fn in rmsg[1:]:
                    if os.path.isfile(fn):
                        mpwriter.append(open(fn, "rb"))
                    else:
                        return web.Response(status=404)
                return web.Response(body=mpwriter, status=200)
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
        testNumber = request.match_info["task"]
        self.server.IDdidNotFinish(data["user"], testNumber)
        return web.json_response(status=200)

    # @routes.get("/ID/randomImage")
    @authenticate_by_token_required_fields(["user"])
    def IDgetImageFromATest(self, data, request):
        # TODO: maybe we want some special message here?
        if data["user"] != "manager":
            return web.Response(status=401)  # only manager

        rmsg = self.server.IDgetImageFromATest()
        if rmsg[0] is False:
            return web.Response(status=410)

        log.debug("Appending file {}".format(rmsg))
        with MultipartWriter("images") as mpwriter:
            for fn in rmsg[1:]:
                if os.path.isfile(fn):
                    mpwriter.append(open(fn, "rb"))
                else:
                    return web.Response(status=404)
            return web.Response(body=mpwriter, status=200)

    @authenticate_by_token_required_fields(["user"])
    def IDdeletePredictions(self, data, request):
        # TODO: maybe we want some special message here?
        if data["user"] != "manager":
            return web.Response(status=401)

        return web.json_response(self.server.IDdeletePredictions(), status=200)

    @authenticate_by_token_required_fields(
        ["user", "rectangle", "fileNumber", "ignoreStamp"]
    )
    def IDrunPredictions(self, data, request):
        # TODO: maybe we want some special message here?
        if data["user"] != "manager":
            return web.Response(status=401)

        rmsg = self.server.IDrunPredictions(
            data["rectangle"], data["fileNumber"], data["ignoreStamp"]
        )
        if rmsg[0]:  # set running or is running
            if rmsg[1]:
                return web.Response(status=200)
            else:
                return web.Response(status=202)  # is already running
        else:  # isn't running because we found a time-stamp
            return web.Response(text=rmsg[1], status=205)

    # @routes.patch("/ID/review")
    @authenticate_by_token_required_fields(["testNumber"])
    def IDreviewID(self, data, request):
        if self.server.IDreviewID(data["testNumber"]):
            return web.Response(status=200)
        else:
            return web.Response(status=404)

    def setUpRoutes(self, router):
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
