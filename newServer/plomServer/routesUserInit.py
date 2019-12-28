from aiohttp import web, MultipartWriter, MultipartReader
import os


class AuthInitHandler:
    def __init__(self, plomServer):
        self.server = plomServer

    # @routes.get("/Version")
    async def version(request):
        return web.Response(
            text="Running Plom server version {} with API {}".format(
                __version__, serverAPI
            ),
            status=200,
        )

    # @routes.delete("/users/{user}")
    async def closeUser(request):
        data = await request.json()
        user = request.match_info["user"]
        if data["user"] != request.match_info["user"]:
            return web.Response(status=400)  # malformed request.
        elif self.server.validate(data["user"], data["token"]):
            self.server.closeUser(data["user"])
            return web.Response(status=200)
        else:
            return web.Response(status=401)

    # @routes.put("/users/{user}")
    async def giveUserToken(request):
        data = await request.json()
        user = request.match_info["user"]

        rmsg = self.server.giveUserToken(data["user"], data["pw"], data["api"])
        if rmsg[0]:
            return web.json_response(rmsg[1], status=200)  # all good, return the token
        elif rmsg[1].startswith("API"):
            return web.json_response(
                rmsg[1], status=400
            )  # api error - return the error message
        else:
            return web.Response(status=401)  # you are not authorised

    # @routes.put("/admin/reloadUsers")
    async def adminReloadUsers(request):
        data = await request.json()

        rmsg = self.server.reloadUsers(data["pw"])
        # returns either True (success) or False (auth-error)
        if rmsg:
            return web.json_response(status=200)  # all good
        else:
            return web.Response(status=401)  # you are not authorised

    def setUpRoutes(self, router):
        router.add_get("/Version", self.version)
        router.add_delete("/users/{user}", self.closeUser)
        router.add_put("/users/{user}", self.giveUserToken)
        router.add_put("/admin/reloadUsers", self.adminReloadUsers)
