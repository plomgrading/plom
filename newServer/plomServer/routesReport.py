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

    def setUpRoutes(self, router):
        router.add_get("/REP/scanned", self.RgetScannedTests)
        router.add_get("/REP/incomplete", self.RgetIncompleteTests)
        router.add_get("/REP/unused", self.RgetUnusedTests)
        router.add_get("/REP/progress", self.RgetProgress)
