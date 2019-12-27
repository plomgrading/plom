from aiohttp import web, MultipartWriter, MultipartReader


class IDHandler:
    def __init__(self, plomServer):
        self.server = plomServer

    # @routes.get("/ID/progress")
    async def IDprogressCount(self, request):
        data = await request.json()
        if self.server.validate(data["user"], data["token"]):
            return web.json_response(self.sever.IDprogressCount(), status=200)
        else:
            return web.Response(status=401)

    # @routes.get("/ID/classlist")
    async def IDrequestClasslist(self, request):
        data = await request.json()
        if self.server.validate(data["user"], data["token"]):
            if os.path.isfile("../resources/classlist.csv"):
                return web.FileResponse("../resources/classlist.csv", status=200)
            else:
                return web.Response(status=404)
        else:
            return web.Response(status=401)

    # @routes.get("/ID/predictions")
    async def IDrequestPredictions(self, request):
        data = await request.json()
        if self.sever.validate(data["user"], data["token"]):
            if os.path.isfile("../resources/predictionlist.csv"):
                return web.FileResponse("../resources/predictionlist.csv", status=200)
            else:
                return web.Response(status=404)
        else:
            return web.Response(status=401)

    # @routes.get("/ID/tasks/complete")
    async def IDrequestDoneTasks(self, request):
        data = await request.json()
        if self.sever.validate(data["user"], data["token"]):
            # return the completed list
            return web.json_response(
                self.sever.IDrequestDoneTasks(data["user"]), status=200
            )
        else:
            return web.Response(status=401)

    # @routes.get("/ID/images/{test}")
    async def IDrequestImage(self, request):
        data = await request.json()
        test = request.match_info["test"]
        if peon.validate(data["user"], data["token"]):
            rmsg = peon.IDrequestImage(data["user"], test)
            if rmsg[0]:  # user allowed access - returns [true, fname0, fname1,...]
                with MultipartWriter("images") as mpwriter:
                    for fn in rmsg[1:]:
                        if os.path.isfile(fn):
                            mpwriter.append(open(fn, "rb"))
                        else:
                            return web.Response(status=404)
                    return web.Response(body=mpwriter, status=200)
            else:
                return web.Response(status=409)  # someone else has that image
        else:
            return web.Response(status=401)  # not authorised at all

    def setUpRoutes(self, router):
        router.add_get("/ID/progress", self.IDprogressCount)
        router.add_get("/ID/classlist", self.IDrequestClasslist)
        router.add_get("/ID/predictions", self.IDrequestPredictions)
        router.add_get("/ID/tasks/complete", self.IDrequestDoneTasks)
        router.add_get("/ID/tasks/{test}", self.IDrequestImage)
