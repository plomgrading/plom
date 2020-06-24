import os
from aiohttp import web, MultipartWriter, MultipartReader

from .routeutils import authenticate_by_token, authenticate_by_token_required_fields


class TotalHandler:
    def __init__(self, plomServer):
        self.server = plomServer

    # @routes.get("/TOT/maxMark")
    @authenticate_by_token
    def TgetMarkMark(self):
        return web.json_response(self.server.TgetMaxMark(), status=200)

    # @routes.get("/TOT/progress")
    @authenticate_by_token
    def TprogressCount(self):
        return web.json_response(self.server.TprogressCount(), status=200)

    # @routes.get("/TOT/tasks/complete")
    @authenticate_by_token_required_fields(["user"])
    def TgetDoneTasks(self, data, request):
        # return the completed list
        return web.json_response(self.server.TgetDoneTasks(data["user"]), status=200)

    # @routes.get("/TOT/image/{test}")
    @authenticate_by_token_required_fields(["user"])
    def TgetImage(self, data, request):
        test = request.match_info["test"]
        rmsg = self.server.TgetImage(data["user"], test)
        if rmsg[0]:  # user allowed access - returns [true, fname0]
            return web.FileResponse(rmsg[1], status=200)
        else:
            return web.Response(status=409)  # someone else has that image

    # @routes.get("/TOT/tasks/available")
    @authenticate_by_token
    def TgetNextTask(self):
        rmsg = self.server.TgetNextTask()  # returns [True, code] or [False]
        if rmsg[0]:
            return web.json_response(rmsg[1], status=200)
        else:
            return web.Response(status=204)  # no papers left

    # @routes.patch("/TOT/tasks/{task}")
    @authenticate_by_token_required_fields(["user"])
    def TclaimThisTask(self, data, request):
        testNumber = request.match_info["task"]
        rmsg = self.server.TclaimThisTask(data["user"], testNumber)
        if rmsg[0]:  # user allowed access - returns [true, fname0]
            return web.FileResponse(rmsg[1], status=200)
        else:
            return web.Response(status=204)  # that task already taken.

    # @routes.put("/TOT/tasks/{task}")
    @authenticate_by_token_required_fields(["user", "mark"])
    def TreturnTotalledTask(self, data, request):
        testNumber = request.match_info["task"]
        rmsg = self.server.TreturnTotalledTask(data["user"], testNumber, data["mark"])
        if rmsg[0]:  # all good
            return web.Response(status=200)
        else:  # a more serious error - can't find this in database
            return web.Response(status=404)

    # @routes.delete("/TOT/tasks/{task}")
    @authenticate_by_token_required_fields(["user"])
    def TdidNotFinish(self, data, request):
        testNumber = request.match_info["task"]
        self.server.TdidNotFinish(data["user"], testNumber)
        return web.json_response(status=200)

    # @routes.patch("/TOT/review")
    @authenticate_by_token_required_fields(["testNumber"])
    def TreviewTotal(self, data, request):
        """Responds with an empty response object indicating if the review Total is possible and the document exists.

        Responds with status 200/404.

        Args:
            data (dict): A dictionary having the user/token in addition to the `testNumber`.
            request (aiohttp.web_request.Request): Request of type PATCH /TOT/review.

        Returns:
            aiohttp.web_fileresponse.FileResponse: An empty response indicating the availability status of
                the review document.
        """

        if self.server.TreviewTotal(data["testNumber"]):
            return web.Response(status=200)
        else:
            return web.Response(status=404)

    def setUpRoutes(self, router):
        router.add_get("/TOT/maxMark", self.TgetMarkMark)
        router.add_get("/TOT/progress", self.TprogressCount)
        router.add_get("/TOT/tasks/complete", self.TgetDoneTasks)
        router.add_get("/TOT/image/{test}", self.TgetImage)
        router.add_get("/TOT/tasks/available", self.TgetNextTask)
        router.add_patch("/TOT/tasks/{task}", self.TclaimThisTask)
        router.add_put("/TOT/tasks/{task}", self.TreturnTotalledTask)
        router.add_delete("/TOT/tasks/{task}", self.TdidNotFinish)
        router.add_patch("/TOT/review", self.TreviewTotal)
