from aiohttp import web, MultipartWriter, MultipartReader
import os
from plomServer.plom_routeutils import authByToken, authByToken_validFields


class TotalHandler:
    def __init__(self, plomServer):
        self.server = plomServer

    # @routes.get("/TOT/maxMark")
    @authByToken
    def TgetMarkMark(self):
        return web.json_response(self.server.TgetMaxMark(), status=200)

    # @routes.get("/TOT/progress")
    @authByToken
    def TprogressCount(self):
        return web.json_response(self.server.TprogressCount(), status=200)

    # @routes.get("/TOT/tasks/complete")
    @authByToken_validFields(["user"])
    def TgetDoneTasks(self, data, request):
        # return the completed list
        return web.json_response(self.server.TgetDoneTasks(data["user"]), status=200)

    # @routes.get("/TOT/image/{test}")
    @authByToken_validFields(["user"])
    def TgetImage(self, data, request):
        test = request.match_info["test"]
        rmsg = self.server.TgetImage(data["user"], test)
        if rmsg[0]:  # user allowed access - returns [true, fname0]
            return web.FileResponse(rmsg[1], status=200)
        else:
            return web.Response(status=409)  # someone else has that image

    # @routes.get("/TOT/tasks/available")
    @authByToken
    def TgetNextTask(self):
        rmsg = self.server.TgetNextTask()  # returns [True, code] or [False]
        if rmsg[0]:
            return web.json_response(rmsg[1], status=200)
        else:
            return web.Response(status=204)  # no papers left

    # @routes.patch("/TOT/tasks/{task}")
    @authByToken_validFields(["user"])
    def TclaimThisTask(self, data, request):
        testNumber = request.match_info["task"]
        rmsg = self.server.TclaimThisTask(data["user"], testNumber)
        if rmsg[0]:  # user allowed access - returns [true, fname0]
            return web.FileResponse(rmsg[1], status=200)
        else:
            return web.Response(status=204)  # that task already taken.

    # @routes.put("/TOT/tasks/{task}")
    @authByToken_validFields(["user", "mark"])
    def TreturnTotalledTask(self, data, request):
        testNumber = request.match_info["task"]
        rmsg = self.server.TreturnTotalledTask(data["user"], testNumber, data["mark"])
        if rmsg[0]:  # all good
            return web.Response(status=200)
        else:  # a more serious error - can't find this in database
            return web.Response(status=404)

    # @routes.delete("/TOT/tasks/{task}")
    @authByToken_validFields(["user"])
    def TdidNotFinish(self, data, request):
        testNumber = request.match_info["task"]
        self.server.TdidNotFinish(data["user"], testNumber)
        return web.json_response(status=200)

    def setUpRoutes(self, router):
        router.add_get("/TOT/maxMark", self.TgetMarkMark)
        router.add_get("/TOT/progress", self.TprogressCount)
        router.add_get("/TOT/tasks/complete", self.TgetDoneTasks)
        router.add_get("/TOT/image/{test}", self.TgetImage)
        router.add_get("/TOT/tasks/available", self.TgetNextTask)
        router.add_patch("/TOT/tasks/{task}", self.TclaimThisTask)
        router.add_put("/TOT/tasks/{task}", self.TreturnTotalledTask)
        router.add_delete("/TOT/tasks/{task}", self.TdidNotFinish)
