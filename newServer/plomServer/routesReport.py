from aiohttp import web, MultipartWriter, MultipartReader
from plomServer.plom_routeutils import authByToken, authByToken_validFields


class ReportHandler:
    def __init__(self, plomServer):
        self.server = plomServer

    # @routes.get("/REP/scanned")
    @authByToken_validFields(["user"])
    def RgetScannedTests(self, d, request):
        if not d["user"] in ("manager", "scanner"):
            return web.Response(status=401)
        return web.json_response(self.server.RgetScannedTests(), status=200)

    # @routes.get("/REP/incomplete")
    @authByToken_validFields(["user"])
    def RgetIncompleteTests(self, d, request):
        if not d["user"] in ("manager", "scanner"):
            return web.Response(status=401)
        return web.json_response(self.server.RgetIncompleteTests(), status=200)

    # @routes.get("/REP/unused")
    @authByToken_validFields(["user"])
    def RgetUnusedTests(self, d, request):
        if not d["user"] in ("manager", "scanner"):
            return web.Response(status=401)
        return web.json_response(self.server.RgetUnusedTests(), status=200)

    # @routes.get("/REP/progress")
    @authByToken_validFields(["user", "q", "v"])
    def RgetProgress(self, d, request):
        if not d["user"] == "manager":
            return web.Response(status=401)
        return web.json_response(self.server.RgetProgress(d["q"], d["v"]), status=200)

    # @routes.get("/REP/questionUserProgress")
    @authByToken_validFields(["user", "q", "v"])
    def RgetQuestionUserProgress(self, d, request):
        if not d["user"] == "manager":
            return web.Response(status=401)
        return web.json_response(
            self.server.RgetQuestionUserProgress(d["q"], d["v"]), status=200
        )

    # @routes.get("/REP/markHistogram")
    @authByToken_validFields(["user", "q", "v"])
    def RgetMarkHistogram(self, d, request):
        if not d["user"] == "manager":
            return web.Response(status=401)
        return web.json_response(
            self.server.RgetMarkHistogram(d["q"], d["v"]), status=200
        )

    # @routes.get("/REP/progress")
    @authByToken_validFields(["user"])
    def RgetIdentified(self, d, request):
        if not d["user"] == "manager":
            return web.Response(status=401)
        return web.json_response(self.server.RgetIdentified(), status=200)

    # @routes.get("/REP/completions")
    @authByToken_validFields(["user"])
    def RgetCompletions(self, d, request):
        if not d["user"] == "manager":
            return web.Response(status=401)
        return web.json_response(self.server.RgetCompletions(), status=200)

    # @routes.get("/REP/status/{test}")
    @authByToken_validFields(["user"])
    def RgetStatus(self, d, request):
        if not d["user"] == "manager":
            return web.Response(status=401)
        testNumber = request.match_info["test"]
        rmsg = self.server.RgetStatus(testNumber)
        if rmsg[0]:
            return web.json_response(rmsg[1], status=200)
        else:
            return web.Response(status=404)

    # @routes.get("/REP/spreadSheet")
    @authByToken_validFields(["user"])
    def RgetSpreadsheet(self, d, request):
        if not d["user"] == "manager":
            return web.Response(status=401)
        rmsg = self.server.RgetSpreadsheet()
        return web.json_response(rmsg, status=200)

    # @routes.get("/REP/coverPageInfo/{test}")
    @authByToken_validFields(["user"])
    def RgetCoverPageInfo(self, d, request):
        if not d["user"] == "manager":
            return web.Response(status=401)
        testNumber = request.match_info["test"]
        rmsg = self.server.RgetCoverPageInfo(testNumber)
        return web.json_response(rmsg, status=200)

    # @routes.get("/REP/originalFiles/{test}")
    @authByToken_validFields(["user"])
    def RgetOriginalFiles(self, d, request):
        if not d["user"] == "manager":
            return web.Response(status=401)
        testNumber = request.match_info["test"]
        rmsg = self.server.RgetOriginalFiles(testNumber)
        if len(rmsg) > 0:
            return web.json_response(rmsg, status=200)
        else:
            return web.Response(status=404)

    # @routes.get("/REP/annotatedFiles/{test}")
    @authByToken_validFields(["user"])
    def RgetAnnotatedFiles(self, d, request):
        if not d["user"] == "manager":
            return web.Response(status=401)
        testNumber = request.match_info["test"]
        rmsg = self.server.RgetAnnotatedFiles(testNumber)
        if len(rmsg) > 0:
            return web.json_response(rmsg, status=200)
        else:
            return web.Response(status=404)

    # @routes.get("/REP/userList")
    @authByToken_validFields(["user"])
    def RgetUserList(self, d, request):
        if not d["user"] == "manager":
            return web.Response(status=401)
        return web.json_response(self.server.RgetUserList(), status=200)

    # @routes.get("/REP/userDetails")
    @authByToken_validFields(["user"])
    def RgetUserDetails(self, d, request):
        if not d["user"] == "manager":
            return web.Response(status=401)
        return web.json_response(self.server.RgetUserDetails(), status=200)

    # @routes.get("/REP/markReview")
    @authByToken_validFields(["user", "filterQ", "filterV", "filterU"])
    def RgetMarkReview(self, d, request):
        if not d["user"] == "manager":
            return web.Response(status=401)
        rmsg = self.server.RgetMarkReview(d["filterQ"], d["filterV"], d["filterU"])
        return web.json_response(rmsg, status=200)

    # @routes.get("/REP/idReview")
    @authByToken_validFields(["user"])
    def RgetIDReview(self, d, request):
        if not d["user"] == "manager":
            return web.Response(status=401)
        rmsg = self.server.RgetIDReview()
        return web.json_response(rmsg, status=200)

    # @routes.get("/REP/totReview")
    @authByToken_validFields(["user"])
    def RgetTotReview(self, d, request):
        if not d["user"] == "manager":
            return web.Response(status=401)
        rmsg = self.server.RgetTotReview()
        return web.json_response(rmsg, status=200)

    # @routes.get("/REP/annotatedImage")
    @authByToken_validFields(["user", "testNumber", "questionNumber", "version"])
    def RgetAnnotatedImage(self, d, request):
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
