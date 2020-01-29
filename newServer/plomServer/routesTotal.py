from aiohttp import web, MultipartWriter, MultipartReader
import os


class TotalHandler:
    def __init__(self, plomServer):
        self.server = plomServer

    # @routes.get("/TOT/maxMark")
    async def TgetMarkMark(self, request):
        data = await request.json()
        if self.server.validate(data["user"], data["token"]):
            return web.json_response(self.server.TgetMaxMark(), status=200)
        else:
            return web.Response(status=401)

    # @routes.get("/TOT/progress")
    async def TprogressCount(self, request):
        data = await request.json()
        if self.server.validate(data["user"], data["token"]):
            return web.json_response(self.server.TprogressCount(), status=200)
        else:
            return web.Response(status=401)

    # @routes.get("/TOT/tasks/complete")
    async def TgetDoneTasks(self, request):
        data = await request.json()
        if self.server.validate(data["user"], data["token"]):
            # return the completed list
            return web.json_response(
                self.server.TgetDoneTasks(data["user"]), status=200
            )
        else:
            return web.Response(status=401)

    # @routes.get("/TOT/image/{test}")
    async def TgetImage(self, request):
        data = await request.json()
        test = request.match_info["test"]
        if self.server.validate(data["user"], data["token"]):
            rmsg = self.server.TgetImage(data["user"], test)
            if rmsg[0]:  # user allowed access - returns [true, fname0]
                return web.FileResponse(rmsg[1], status=200)
            else:
                return web.Response(status=409)  # someone else has that image
        else:
            return web.Response(status=401)  # not authorised at all

    # @routes.get("/TOT/tasks/available")
    async def TgetNextTask(self, request):
        data = await request.json()
        if self.server.validate(data["user"], data["token"]):
            rmsg = self.server.TgetNextTask()  # returns [True, code] or [False]
            if rmsg[0]:
                return web.json_response(rmsg[1], status=200)
            else:
                return web.Response(status=204)  # no papers left
        else:
            return web.Response(status=401)

    # @routes.patch("/TOT/tasks/{task}")
    async def TclaimThisTask(self, request):
        data = await request.json()
        testNumber = request.match_info["task"]
        if self.server.validate(data["user"], data["token"]):
            rmsg = self.server.TclaimThisTask(data["user"], testNumber)
            if rmsg[0]:  # user allowed access - returns [true, fname0]
                return web.FileResponse(rmsg[1], status=200)
            else:
                return web.Response(status=204)  # that task already taken.
        else:
            return web.Response(status=401)

    # @routes.put("/TOT/tasks/{task}")
    async def TreturnTotalledTask(self, request):
        data = await request.json()
        testNumber = request.match_info["task"]
        if self.server.validate(data["user"], data["token"]):
            rmsg = self.server.TreturnTotalledTask(
                data["user"], testNumber, data["mark"]
            )
            # returns [True] if all good
            # [False] - if error
            if rmsg[0]:  # all good
                return web.Response(status=200)
            else:  # a more serious error - can't find this in database
                return web.Response(status=404)
        else:
            return web.Response(status=401)

    # @routes.delete("/TOT/tasks/{task}")
    async def TdidNotFinish(self, request):
        data = await request.json()
        testNumber = request.match_info["task"]
        if self.server.validate(data["user"], data["token"]):
            self.server.TdidNotFinish(data["user"], testNumber)
            return web.json_response(status=200)
        else:
            return web.Response(status=401)

    def setUpRoutes(self, router):
        router.add_get("/TOT/maxMark", self.TgetMarkMark)
        router.add_get("/TOT/progress", self.TprogressCount)
        router.add_get("/TOT/tasks/complete", self.TgetDoneTasks)
        router.add_get("/TOT/image/{test}", self.TgetImage)
        router.add_get("/TOT/tasks/available", self.TgetNextTask)
        router.add_patch("/TOT/tasks/{task}", self.TclaimThisTask)
        router.add_put("/TOT/tasks/{task}", self.TreturnTotalledTask)
        router.add_delete("/TOT/tasks/{task}", self.TdidNotFinish)
