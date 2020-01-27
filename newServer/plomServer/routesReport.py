from aiohttp import web, MultipartWriter, MultipartReader


class ReportHandler:
    def __init__(self, plomServer):
        self.server = plomServer

    # @routes.get("/REP/scanned")
    async def RgetScannedTests(self, request):
        data = await request.json()
        if self.server.validate(data["user"], data["token"]) and data["user"] in [
            "manager",
            "scanner",
        ]:
            return web.json_response(self.server.RgetScannedTests(), status=200)
        else:
            return web.Response(status=401)

    # @routes.get("/REP/incomplete")
    async def RgetIncompleteTests(self, request):
        data = await request.json()
        if self.server.validate(data["user"], data["token"]) and data["user"] in [
            "manager",
            "scanner",
        ]:
            return web.json_response(self.server.RgetIncompleteTests(), status=200)
        else:
            return web.Response(status=401)

    # @routes.get("/REP/unused")
    async def RgetUnusedTests(self, request):
        data = await request.json()
        if self.server.validate(data["user"], data["token"]) and data["user"] in [
            "manager",
            "scanner",
        ]:
            return web.json_response(self.server.RgetUnusedTests(), status=200)
        else:
            return web.Response(status=401)

    # @routes.get("/REP/progress")
    async def RgetProgress(self, request):
        data = await request.json()
        if (
            self.server.validate(data["user"], data["token"])
            and data["user"] == "manager"
        ):
            return web.json_response(
                self.server.RgetProgress(data["q"], data["v"]), status=200
            )
        else:
            return web.Response(status=401)

    # @routes.get("/REP/markHistogram")
    async def RgetMarkHistogram(self, request):
        data = await request.json()
        if (
            self.server.validate(data["user"], data["token"])
            and data["user"] == "manager"
        ):
            return web.json_response(
                self.server.RgetMarkHistogram(data["q"], data["v"]), status=200
            )
        else:
            return web.Response(status=401)

    # @routes.get("/REP/progress")
    async def RgetIdentified(self, request):
        data = await request.json()
        if (
            self.server.validate(data["user"], data["token"])
            and data["user"] == "manager"
        ):
            return web.json_response(self.server.RgetIdentified(), status=200)
        else:
            return web.Response(status=401)

    async def RgetCompletions(self, request):
        data = await request.json()
        if (
            self.server.validate(data["user"], data["token"])
            and data["user"] == "manager"
        ):
            return web.json_response(self.server.RgetCompletions(), status=200)
        else:
            return web.Response(status=401)

    async def RgetStatus(self, request):
        testNumber = request.match_info["test"]
        data = await request.json()
        if (
            self.server.validate(data["user"], data["token"])
            and data["user"] == "manager"
        ):
            rmsg = self.server.RgetStatus(testNumber)
            if rmsg[0]:
                return web.json_response(rmsg[1], status=200)
            else:
                return web.Response(status=404)
        else:
            return web.Response(status=401)

    async def RgetSpreadsheet(self, request):
        data = await request.json()
        if (
            self.server.validate(data["user"], data["token"])
            and data["user"] == "manager"
        ):
            rmsg = self.server.RgetSpreadsheet()
            return web.json_response(rmsg, status=200)
        else:
            return web.Response(status=401)

    async def RgetCoverPageInfo(self, request):
        testNumber = request.match_info["test"]
        data = await request.json()
        if (
            self.server.validate(data["user"], data["token"])
            and data["user"] == "manager"
        ):
            rmsg = self.server.RgetCoverPageInfo(testNumber)
            return web.json_response(rmsg, status=200)
        else:
            return web.Response(status=401)

    async def RgetOriginalFiles(self, request):
        testNumber = request.match_info["test"]
        data = await request.json()
        if (
            self.server.validate(data["user"], data["token"])
            and data["user"] == "manager"
        ):
            rmsg = self.server.RgetOriginalFiles(testNumber)
            if len(rmsg) > 0:
                return web.json_response(rmsg, status=200)
            else:
                return web.Response(status=404)
        else:
            return web.Response(status=401)

    async def RgetAnnotatedFiles(self, request):
        testNumber = request.match_info["test"]
        data = await request.json()
        if (
            self.server.validate(data["user"], data["token"])
            and data["user"] == "manager"
        ):
            rmsg = self.server.RgetAnnotatedFiles(testNumber)
            if len(rmsg) > 0:
                return web.json_response(rmsg, status=200)
            else:
                return web.Response(status=404)
        else:
            return web.Response(status=401)

    async def RgetUserList(self, request):
        data = await request.json()
        if (
            self.server.validate(data["user"], data["token"])
            and data["user"] == "manager"
        ):
            rmsg = sorted([x for x in self.server.userList.keys()])
            return web.json_response(rmsg, status=200)
        else:
            return web.Response(status=401)

    async def RgetMarkReview(self, request):
        data = await request.json()
        if (
            self.server.validate(data["user"], data["token"])
            and data["user"] == "manager"
        ):
            rmsg = self.server.RgetMarkReview(
                data["filterQ"], data["filterV"], data["filterU"]
            )
            return web.json_response(rmsg, status=200)
        else:
            return web.Response(status=401)

    async def RgetIDReview(self, request):
        data = await request.json()
        if (
            self.server.validate(data["user"], data["token"])
            and data["user"] == "manager"
        ):
            rmsg = self.server.RgetIDReview()
            return web.json_response(rmsg, status=200)
        else:
            return web.Response(status=401)

    async def RgetAnnotatedImage(self, request):
        data = await request.json()
        if (
            self.server.validate(data["user"], data["token"])
            and data["user"] == "manager"
        ):
            rmsg = self.server.RgetAnnotatedImage(
                data["testNumber"], data["questionNumber"], data["version"]
            )
            if rmsg[0]:
                return web.FileResponse(rmsg[1], status=200)
            else:
                return web.Response(status=404)
        else:
            return web.Response(status=401)

    def setUpRoutes(self, router):
        router.add_get("/REP/scanned", self.RgetScannedTests)
        router.add_get("/REP/incomplete", self.RgetIncompleteTests)
        router.add_get("/REP/unused", self.RgetUnusedTests)
        router.add_get("/REP/progress", self.RgetProgress)
        router.add_get("/REP/markHistogram", self.RgetMarkHistogram)
        router.add_get("/REP/identified", self.RgetIdentified)
        router.add_get("/REP/completions", self.RgetCompletions)
        router.add_get("/REP/status/{test}", self.RgetStatus)
        router.add_get("/REP/spreadSheet", self.RgetSpreadsheet)
        router.add_get("/REP/originalFiles/{test}", self.RgetOriginalFiles)
        router.add_get("/REP/coverPageInfo/{test}", self.RgetCoverPageInfo)
        router.add_get("/REP/annotatedFiles/{test}", self.RgetAnnotatedFiles)
        router.add_get("/REP/userList", self.RgetUserList)
        router.add_get("/REP/markReview", self.RgetMarkReview)
        router.add_get("/REP/idReview", self.RgetIDReview)
        router.add_get("/REP/annotatedImage", self.RgetAnnotatedImage)
