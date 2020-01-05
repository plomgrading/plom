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

        if not (
            self.server.validate(param["user"], param["token"])
            and param["user"] in ["manager", "scanner",]
        ):  # not authorised!
            return web.Response(status=401)

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
        data = await request.json()
        if self.server.validate(data["user"], data["token"]) and data["user"] in [
            "manager",
            "scanner",
        ]:
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
            rmsg = self.server.addUnknownPage(
                param["fileName"], image, param["md5sum"],
            )
            return web.json_response(rmsg, status=200)  # all good
        else:
            return web.Response(status=401)

    async def uploadCollidingPage(self, request):
        data = await request.json()
        if self.server.validate(data["user"], data["token"]) and data["user"] in [
            "manager",
            "scanner",
        ]:
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
        else:
            return web.Response(status=401)

    async def replaceMissingPage(self, request):
        code = request.match_info["tpv"]
        data = await request.json()
        if (
            self.server.validate(data["user"], data["token"])
            and data["user"] == "manager"
        ):
            rval = self.server.replaceMissingPage(
                data["test"], data["page"], data["version"]
            )
            if rval[0]:
                if rval[1]:
                    return web.json_response(rval, status=200)  # all fine
                else:
                    return web.Response(status=409)  # page already scanned
            else:
                return web.Response(status=404)  # page not found at all
        else:
            return web.Response(status=401)

    def setUpRoutes(self, router):
        router.add_put("/admin/knownPages/{tpv}", self.uploadKnownPage)
        router.add_put("/admin/unknownPages", self.uploadUnknownPage)
        router.add_put("/admin/collidingPages/{tpv}", self.uploadCollidingPage)
        router.add_put("/admin/missingPage/{tpv}", self.replaceMissingPage)
