from aiohttp import web, MultipartWriter, MultipartReader

from .routeutils import authenticate_by_token, authenticate_by_token_required_fields


class ReportHandler:
    def __init__(self, plomServer):
        self.server = plomServer

    # @routes.get("/REP/scanned")
    @authenticate_by_token_required_fields(["user"])
    def RgetScannedTests(self, d, request):
        if not d["user"] in ("manager", "scanner"):
            return web.Response(status=401)
        return web.json_response(self.server.RgetScannedTests(), status=200)

    # @routes.get("/REP/incomplete")
    @authenticate_by_token_required_fields(["user"])
    def RgetIncompleteTests(self, d, request):
        if not d["user"] in ("manager", "scanner"):
            return web.Response(status=401)
        return web.json_response(self.server.RgetIncompleteTests(), status=200)

    # @routes.get("/REP/unused")
    @authenticate_by_token_required_fields(["user"])
    def RgetUnusedTests(self, d, request):
        if not d["user"] in ("manager", "scanner"):
            return web.Response(status=401)
        return web.json_response(self.server.RgetUnusedTests(), status=200)

    # @routes.get("/REP/progress")
    @authenticate_by_token_required_fields(["user", "q", "v"])
    def RgetProgress(self, d, request):
        if not d["user"] == "manager":
            return web.Response(status=401)
        return web.json_response(self.server.RgetProgress(d["q"], d["v"]), status=200)

    # @routes.get("/REP/questionUserProgress")
    @authenticate_by_token_required_fields(["user", "q", "v"])
    def RgetQuestionUserProgress(self, d, request):
        if not d["user"] == "manager":
            return web.Response(status=401)
        return web.json_response(
            self.server.RgetQuestionUserProgress(d["q"], d["v"]), status=200
        )

    # @routes.get("/REP/markHistogram")
    @authenticate_by_token_required_fields(["user", "q", "v"])
    def RgetMarkHistogram(self, d, request):
        if not d["user"] == "manager":
            return web.Response(status=401)
        return web.json_response(
            self.server.RgetMarkHistogram(d["q"], d["v"]), status=200
        )

    # @routes.get("/REP/progress")
    @authenticate_by_token_required_fields(["user"])
    def RgetIdentified(self, d, request):
        if not d["user"] == "manager":
            return web.Response(status=401)
        return web.json_response(self.server.RgetIdentified(), status=200)

    # @routes.get("/REP/completionStatus")
    @authenticate_by_token_required_fields(["user"])
    def RgetCompletionStatus(self, d, request):
        if not d["user"] == "manager":
            return web.Response(status=401)
        return web.json_response(self.server.RgetCompletionStatus(), status=200)

    # @routes.get("/REP/outToDo")
    @authenticate_by_token_required_fields(["user"])
    def RgetOutToDo(self, d, request):
        if not d["user"] == "manager":
            return web.Response(status=401)
        return web.json_response(self.server.RgetOutToDo(), status=200)

    # @routes.get("/REP/marked")
    @authenticate_by_token_required_fields(["user", "q", "v"])
    def RgetMarked(self, d, request):
        if not d["user"] == "manager":
            return web.Response(status=401)
        return web.json_response(self.server.RgetMarked(d["q"], d["v"]), status=200)

    # @routes.get("/REP/status/{test}")
    @authenticate_by_token_required_fields(["user"])
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
    @authenticate_by_token_required_fields(["user"])
    def RgetSpreadsheet(self, d, request):
        if not d["user"] == "manager":
            return web.Response(status=401)
        rmsg = self.server.RgetSpreadsheet()
        return web.json_response(rmsg, status=200)

    # @routes.get("/REP/coverPageInfo/{test}")
    @authenticate_by_token_required_fields(["user"])
    def RgetCoverPageInfo(self, d, request):
        if not d["user"] == "manager":
            return web.Response(status=401)
        testNumber = request.match_info["test"]
        rmsg = self.server.RgetCoverPageInfo(testNumber)
        return web.json_response(rmsg, status=200)

    # @routes.get("/REP/originalFiles/{test}")
    @authenticate_by_token_required_fields(["user"])
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
    @authenticate_by_token_required_fields(["user"])
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
    @authenticate_by_token_required_fields(["user"])
    def RgetUserList(self, d, request):
        if not d["user"] == "manager":
            return web.Response(status=401)
        return web.json_response(self.server.RgetUserList(), status=200)

    # @routes.get("/REP/userDetails")
    @authenticate_by_token_required_fields(["user"])
    def RgetUserDetails(self, d, request):
        if not d["user"] == "manager":
            return web.Response(status=401)
        return web.json_response(self.server.RgetUserDetails(), status=200)

    # @routes.get("/REP/markReview")
    @authenticate_by_token_required_fields(["user", "filterQ", "filterV", "filterU"])
    def RgetMarkReview(self, d, request):
        if not d["user"] == "manager":
            return web.Response(status=401)
        rmsg = self.server.RgetMarkReview(d["filterQ"], d["filterV"], d["filterU"])
        return web.json_response(rmsg, status=200)

    # @routes.get("/REP/idReview")
    @authenticate_by_token_required_fields(["user"])
    def RgetIDReview(self, d, request):
        if not d["user"] == "manager":
            return web.Response(status=401)
        rmsg = self.server.RgetIDReview()
        return web.json_response(rmsg, status=200)

    # @routes.get("/REP/totReview")
    @authenticate_by_token_required_fields(["user"])
    def RgetTotReview(self, d, request):
        if not d["user"] == "manager":
            return web.Response(status=401)
        rmsg = self.server.RgetTotReview()
        return web.json_response(rmsg, status=200)

    # @routes.get("/REP/annotatedImage")
    @authenticate_by_token_required_fields(
        ["user", "testNumber", "questionNumber", "version"]
    )
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
        router.add_get("/REP/marked", self.RgetMarked)
        router.add_get("/REP/identified", self.RgetIdentified)
        router.add_get("/REP/completionStatus", self.RgetCompletionStatus)
        router.add_get("/REP/outToDo", self.RgetOutToDo)
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
