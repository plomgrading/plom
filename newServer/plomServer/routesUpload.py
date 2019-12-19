from aiohttp import web, MultipartWriter, MultipartReader


class UploadHandler:
    def __init__(self, plomServer):
        self.server = plomServer

    async def uploadKnownPage(self, request):
        reader = MultipartReader.from_response(request)
        code = request.match_info["tpv"]

        part0 = await reader.next()  # should be parameters
        if part0 is None:  # weird error
            return web.Response(status=406)  # should have sent 3 parts
        param = await part0.json()

        part1 = await reader.next()  # should be the image file
        if part1 is None:  # weird error
            return web.Response(status=406)  # should have sent 3 parts
        image = await part1.read()
        # file it away.
        rmsg = self.server.addKnownPage(
            param["test"],
            param["page"],
            param["version"],
            param["fileName"],
            image,
            param["md5sum"],
        )
        return web.json_response(rmsg, status=200)  # all good

    async def uploadUnknownPage(self, request):
        reader = MultipartReader.from_response(request)

        part0 = await reader.next()  # should be parameters
        if part0 is None:  # weird error
            return web.Response(status=406)  # should have sent 3 parts
        param = await part0.json()

        part1 = await reader.next()  # should be the image file
        if part1 is None:  # weird error
            return web.Response(status=406)  # should have sent 3 parts
        image = await part1.read()
        # file it away.
        rmsg = self.server.addUnknownPage(param["fileName"], image, param["md5sum"],)
        return web.json_response(rmsg, status=200)  # all good

    async def uploadCollidingPage(self, request):
        reader = MultipartReader.from_response(request)
        code = request.match_info["tpv"]

        part0 = await reader.next()  # should be parameters
        if part0 is None:  # weird error
            return web.Response(status=406)  # should have sent 3 parts
        param = await part0.json()

        part1 = await reader.next()  # should be the image file
        if part1 is None:  # weird error
            return web.Response(status=406)  # should have sent 3 parts
        image = await part1.read()
        # file it away.
        rmsg = self.server.addCollidingPage(
            param["test"],
            param["page"],
            param["version"],
            param["fileName"],
            image,
            param["md5sum"],
        )
        return web.json_response(rmsg, status=200)  # all good

    def setUpRoutes(self, router):
        router.add_put("/admin/knownPages/{tpv}", self.uploadKnownPage)
        router.add_put("/admin/unknownPages", self.uploadUnknownPage)
        router.add_put("/admin/collidingPages/{tpv}", self.uploadCollidingPage)
