from aiohttp import web, MultipartWriter, MultipartReader


# TODO: in some common_utils.py?
def validFields(d, fields):
    """Check that input dict has (and only has) expected fields."""
    return set(d.keys()) == set(fields)


class ReportHandler:
    def __init__(self, plomServer):
        self.server = plomServer

    # @routes.get("/REP/scanned")
    async def RgetScannedTests(self, request):
        d = await request.json()
        if not validFields(d, ["user", "token"]):
            return web.Response(status=400)
        if not self.server.validate(d["user"], d["token"]):
            return web.Response(status=401)
        if not d["user"] in ("manager", "scanner"):
            return web.Response(status=401)

        return web.json_response(self.server.RgetScannedTests(), status=200)

    # @routes.get("/REP/incomplete")
    async def RgetIncompleteTests(self, request):
        d = await request.json()
        if not validFields(d, ["user", "token"]):
            return web.Response(status=400)
        if not self.server.validate(d["user"], d["token"]):
            return web.Response(status=401)
        if not d["user"] in ("manager", "scanner"):
            return web.Response(status=401)

        return web.json_response(self.server.RgetIncompleteTests(), status=200)

    # @routes.get("/REP/unused")
    async def RgetUnusedTests(self, request):
        d = await request.json()
        if not validFields(d, ["user", "token"]):
            return web.Response(status=400)
        if not self.server.validate(d["user"], d["token"]):
            return web.Response(status=401)
        if not d["user"] in ("manager", "scanner"):
            return web.Response(status=401)

        return web.json_response(self.server.RgetUnusedTests(), status=200)

    # @routes.get("/REP/progress")
    async def RgetProgress(self, request):
        d = await request.json()
        if not validFields(d, ["user", "token", "q", "v"]):
            return web.Response(status=400)
        if not self.server.validate(d["user"], d["token"]):
            return web.Response(status=401)
        if not d["user"] == "manager":
            return web.Response(status=401)

        return web.json_response(self.server.RgetProgress(d["q"], d["v"]), status=200)

    # @routes.get("/REP/questionUserProgress")
    async def RgetQuestionUserProgress(self, request):
        data = await request.json()
        if (
            self.server.validate(data["user"], data["token"])
            and data["user"] == "manager"
        ):
            return web.json_response(
                self.server.RgetQuestionUserProgress(data["q"], data["v"]), status=200
            )
        else:
            return web.Response(status=401)

    # @routes.get("/REP/markHistogram")
    async def RgetMarkHistogram(self, request):
        d = await request.json()
        if not validFields(d, ["user", "token", "q", "v"]):
            return web.Response(status=400)
        if not self.server.validate(d["user"], d["token"]):
            return web.Response(status=401)
        if not d["user"] == "manager":
            return web.Response(status=401)

        return web.json_response(
            self.server.RgetMarkHistogram(d["q"], d["v"]), status=200
        )

    # @routes.get("/REP/progress")
    async def RgetIdentified(self, request):
        d = await request.json()
        if not validFields(d, ["user", "token"]):
            return web.Response(status=400)
        if not self.server.validate(d["user"], d["token"]):
            return web.Response(status=401)
        if not d["user"] == "manager":
            return web.Response(status=401)

        return web.json_response(self.server.RgetIdentified(), status=200)

    async def RgetCompletions(self, request):
        d = await request.json()
        if not validFields(d, ["user", "token"]):
            return web.Response(status=400)
        if not self.server.validate(d["user"], d["token"]):
            return web.Response(status=401)
        if not d["user"] == "manager":
            return web.Response(status=401)

        return web.json_response(self.server.RgetCompletions(), status=200)

    async def RgetStatus(self, request):
        d = await request.json()
        if not validFields(d, ["user", "token"]):
            return web.Response(status=400)
        if not self.server.validate(d["user"], d["token"]):
            return web.Response(status=401)
        if not d["user"] == "manager":
            return web.Response(status=401)

        testNumber = request.match_info["test"]
        rmsg = self.server.RgetStatus(testNumber)
        if rmsg[0]:
            return web.json_response(rmsg[1], status=200)
        else:
            return web.Response(status=404)

    async def RgetSpreadsheet(self, request):
        d = await request.json()
        if not validFields(d, ["user", "token"]):
            return web.Response(status=400)
        if not self.server.validate(d["user"], d["token"]):
            return web.Response(status=401)
        if not d["user"] == "manager":
            return web.Response(status=401)

        rmsg = self.server.RgetSpreadsheet()
        return web.json_response(rmsg, status=200)

    async def RgetCoverPageInfo(self, request):
        d = await request.json()
        if not validFields(d, ["user", "token"]):
            return web.Response(status=400)
        if not self.server.validate(d["user"], d["token"]):
            return web.Response(status=401)
        if not d["user"] == "manager":
            return web.Response(status=401)

        testNumber = request.match_info["test"]
        rmsg = self.server.RgetCoverPageInfo(testNumber)
        return web.json_response(rmsg, status=200)

    async def RgetOriginalFiles(self, request):
        d = await request.json()
        if not validFields(d, ["user", "token"]):
            return web.Response(status=400)
        if not self.server.validate(d["user"], d["token"]):
            return web.Response(status=401)
        if not d["user"] == "manager":
            return web.Response(status=401)

        testNumber = request.match_info["test"]
        rmsg = self.server.RgetOriginalFiles(testNumber)
        if len(rmsg) > 0:
            return web.json_response(rmsg, status=200)
        else:
            return web.Response(status=404)

    async def RgetAnnotatedFiles(self, request):
        d = await request.json()
        if not validFields(d, ["user", "token"]):
            return web.Response(status=400)
        if not self.server.validate(d["user"], d["token"]):
            return web.Response(status=401)
        if not d["user"] == "manager":
            return web.Response(status=401)

        testNumber = request.match_info["test"]
        rmsg = self.server.RgetAnnotatedFiles(testNumber)
        if len(rmsg) > 0:
            return web.json_response(rmsg, status=200)
        else:
            return web.Response(status=404)

    async def RgetUserList(self, request):
        d = await request.json()
        if not validFields(d, ["user", "token"]):
            return web.Response(status=400)
        if not self.server.validate(d["user"], d["token"]):
            return web.Response(status=401)
        if not d["user"] == "manager":
            return web.Response(status=401)

        return web.json_response(self.server.RgetUserList(), status=200)

    async def RgetUserDetails(self, request):
        d = await request.json()
        if not validFields(d, ["user", "token"]):
            return web.Response(status=400)
        if not self.server.validate(d["user"], d["token"]):
            return web.Response(status=401)
        if not d["user"] == "manager":
            return web.Response(status=401)

        return web.json_response(self.server.RgetUserDetails(), status=200)

    async def RgetMarkReview(self, request):
        d = await request.json()
        if not validFields(d, ["user", "token", "filterQ", "filterV", "filterU"]):
            return web.Response(status=400)
        if not self.server.validate(d["user"], d["token"]):
            return web.Response(status=401)
        if not d["user"] == "manager":
            return web.Response(status=401)

        rmsg = self.server.RgetMarkReview(d["filterQ"], d["filterV"], d["filterU"])
        return web.json_response(rmsg, status=200)

    async def RgetIDReview(self, request):
        d = await request.json()
        if not validFields(d, ["user", "token"]):
            return web.Response(status=400)
        if not self.server.validate(d["user"], d["token"]):
            return web.Response(status=401)
        if not d["user"] == "manager":
            return web.Response(status=401)

        rmsg = self.server.RgetIDReview()
        return web.json_response(rmsg, status=200)

    async def RgetTotReview(self, request):
        d = await request.json()
        if not validFields(d, ["user", "token"]):
            return web.Response(status=400)
        if not self.server.validate(d["user"], d["token"]):
            return web.Response(status=401)
        if not d["user"] == "manager":
            return web.Response(status=401)

        rmsg = self.server.RgetTotReview()
        return web.json_response(rmsg, status=200)

    async def RgetAnnotatedImage(self, request):
        d = await request.json()
        if not validFields(
            d, ["user", "token", "testNumber", "questionNumber", "version"]
        ):
            return web.Response(status=400)
        if not self.server.validate(d["user"], d["token"]):
            return web.Response(status=401)
        if not d["user"] == "manager":
            return web.Response(status=401)

        rmsg = self.server.RgetAnnotatedImage(
            d["testNumber"], d["questionNumber"], d["version"]
        )
        if rmsg[0]:
            return web.FileResponse(rmsg[1], status=200)
        else:
            return web.Response(status=404)

    def setUpRoutes(self, router):
        router.add_get("/REP/scanned", self.RgetScannedTests)
        router.add_get("/REP/incomplete", self.RgetIncompleteTests)
        router.add_get("/REP/unused", self.RgetUnusedTests)
        router.add_get("/REP/progress", self.RgetProgress)
        router.add_get("/REP/questionUserProgress", self.RgetQuestionUserProgress)
        router.add_get("/REP/markHistogram", self.RgetMarkHistogram)
        router.add_get("/REP/identified", self.RgetIdentified)
        router.add_get("/REP/completions", self.RgetCompletions)
        router.add_get("/REP/status/{test}", self.RgetStatus)
        router.add_get("/REP/spreadSheet", self.RgetSpreadsheet)
        router.add_get("/REP/originalFiles/{test}", self.RgetOriginalFiles)
        router.add_get("/REP/coverPageInfo/{test}", self.RgetCoverPageInfo)
        router.add_get("/REP/annotatedFiles/{test}", self.RgetAnnotatedFiles)
        router.add_get("/REP/userList", self.RgetUserList)
        router.add_get("/REP/userDetails", self.RgetUserDetails)
        router.add_get("/REP/markReview", self.RgetMarkReview)
        router.add_get("/REP/idReview", self.RgetIDReview)
        router.add_get("/REP/totReview", self.RgetTotReview)
        router.add_get("/REP/annotatedImage", self.RgetAnnotatedImage)
