from aiohttp import web, MultipartWriter, MultipartReader


class ReportHandler:
    def __init__(self, plomServer):
        self.server = plomServer

    # @routes.get("/REP/scanned")
    async def RgetScannedTests(self, request):
        return web.json_response(self.server.RgetScannedTests(), status=200)

    # @routes.get("/REP/incomplete")
    async def RgetIncompleteTests(self, request):
        return web.json_response(self.server.RgetIncompleteTests(), status=200)

    # @routes.get("/REP/unused")
    async def RgetUnusedTests(self, request):
        return web.json_response(self.server.RgetUnusedTests(), status=200)

    # @routes.get("/REP/progress")
    async def RgetUnusedTests(self, request):
        data = await request.json()
        return web.json_response(
            self.server.RgetUnusedTests(data["q"], data["v"]), status=200
        )

    def setUpRoutes(self, router):
        router.add_get("/REP/scanned", self.RgetScannedTests)
        router.add_get("/REP/incomplete", self.RgetIncompleteTests)
        router.add_get("/REP/unused", self.RgetUnusedTests)
        router.add_get("/REP/progress", self.RgetProgress)
