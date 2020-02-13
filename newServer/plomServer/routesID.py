from aiohttp import web, MultipartWriter, MultipartReader
import os
from plomServer.plom_routeutils import authByToken, authByToken_validFields
from plomServer.plom_routeutils import validFields

# I couldn't make this work with the auth deco
# routes = web.RouteTableDef()


class IDHandler:
    def __init__(self, plomServer):
        self.server = plomServer
        # self.local_route_table = routes

    # @routes.get("/ID/progress")
    @authByToken
    def IDprogressCount(self):
        return web.json_response(self.server.IDprogressCount(), status=200)

    # @routes.get("/ID/classlist")
    @authByToken
    def IDgetClasslist(self):
        if os.path.isfile("../resources/classlist.csv"):
            return web.FileResponse("../resources/classlist.csv", status=200)
        else:
            return web.Response(status=404)

    # @routes.get("/ID/predictions")
    async def IDgetPredictions(self, request):
        data = await request.json()
        if self.server.validate(data["user"], data["token"]):
            if os.path.isfile("../resources/predictionlist.csv"):
                return web.FileResponse("../resources/predictionlist.csv", status=200)
            else:
                return web.Response(status=404)
        else:
            return web.Response(status=401)

    # @routes.get("/ID/tasks/complete")
    async def IDgetDoneTasks(self, request):
        data = await request.json()
        if not validFields(data, ["user", "token"]):
            return web.Response(status=400)
        if not self.server.validate(data["user"], data["token"]):
            return web.Response(status=401)

        # return the completed list
        return web.json_response(self.server.IDgetDoneTasks(data["user"]), status=200)

    # @routes.get("/ID/images/{test}")
    @authByToken_validFields(["user"])
    def IDgetImage(self, data, request):
        test = request.match_info["test"]
        rmsg = self.server.IDgetImage(data["user"], test)
        if not rmsg[0]:  # user allowed access - returns [true, fname0, fname1,...]
            return web.Response(status=409)  # someone else has that image
        with MultipartWriter("images") as mpwriter:
            for fn in rmsg[1:]:
                if os.path.isfile(fn):
                    mpwriter.append(open(fn, "rb"))
                else:
                    return web.Response(status=404)
            return web.Response(body=mpwriter, status=200)

    # @routes.get("/ID/tasks/available")
    async def IDgetNextTask(self, request):
        data = await request.json()
        if not validFields(data, ["user", "token"]):
            return web.Response(status=400)
        if not self.server.validate(data["user"], data["token"]):
            return web.Response(status=401)

        rmsg = self.server.IDgetNextTask()  # returns [True, code] or [False]
        if rmsg[0]:
            return web.json_response(rmsg[1], status=200)
        else:
            return web.Response(status=204)  # no papers left

    # @routes.patch("/ID/tasks/{task}")
    async def IDclaimThisTask(self, request):
        data = await request.json()
        if not validFields(data, ["user", "token"]):
            return web.Response(status=400)
        if not self.server.validate(data["user"], data["token"]):
            return web.Response(status=401)

        testNumber = request.match_info["task"]
        rmsg = self.server.IDclaimThisTask(data["user"], testNumber)
        if rmsg[0]:  # user allowed access - returns [true, fname0, fname1,...]
            with MultipartWriter("images") as mpwriter:
                for fn in rmsg[1:]:
                    if os.path.isfile(fn):
                        mpwriter.append(open(fn, "rb"))
                    else:
                        return web.Response(status=404)
                return web.Response(body=mpwriter, status=200)
        else:
            return web.Response(status=204)  # that task already taken.

    # @routes.put("/ID/tasks/{task}")
    @authByToken_validFields(["user", "sid", "sname"])
    def IDreturnIDdTask(self, data):
        testNumber = request.match_info["task"]
        rmsg = self.server.IDreturnIDdTask(
            data["user"], testNumber, data["sid"], data["sname"]
        )
        # returns [True] if all good
        # [False, True] - if student number already in use
        # [False, False] - if bigger error
        if rmsg[0]:  # all good
            return web.Response(status=200)
        elif rmsg[1]:  # student number already in use
            return web.Response(status=409)
        else:  # a more serious error - can't find this in database
            return web.Response(status=404)

    # @routes.delete("/ID/tasks/{task}")
    async def IDdidNotFinishTask(self, request):
        data = await request.json()
        if not validFields(data, ["user", "token"]):
            return web.Response(status=400)
        if not self.server.validate(data["user"], data["token"]):
            return web.Response(status=401)

        testNumber = request.match_info["task"]
        self.server.IDdidNotFinish(data["user"], testNumber)
        return web.json_response(status=200)

    # @routes.get("/ID/randomImage")
    async def IDgetRandomImage(self, request):
        data = await request.json()
        if not validFields(data, ["user", "token"]):
            return web.Response(status=400)
        if not self.server.validate(data["user"], data["token"]):
            return web.Response(status=401)

        # TODO: maybe we want some special message here?
        if data["user"] != "manager":
            return web.Response(status=401)  # only manager

        rmsg = self.server.IDgetRandomImage()
        print("Appending file {}".format(rmsg))
        with MultipartWriter("images") as mpwriter:
            for fn in rmsg[1:]:
                if os.path.isfile(fn):
                    mpwriter.append(open(fn, "rb"))
                else:
                    return web.Response(status=404)
            return web.Response(body=mpwriter, status=200)

    async def IDdeletePredictions(self, request):
        data = await request.json()
        if not validFields(data, ["user", "token"]):
            return web.Response(status=400)
        if not self.server.validate(data["user"], data["token"]):
            return web.Response(status=401)

        # TODO: maybe we want some special message here?
        if data["user"] != "manager":
            return web.Response(status=401)

        return web.json_response(self.server.IDdeletePredictions(), status=200)

    # @routes.patch("/ID/review")
    async def IDreviewID(self, request):
        data = await request.json()
        if not validFields(data, ["user", "token", "testNumber"]):
            return web.Response(status=400)
        if not self.server.validate(data["user"], data["token"]):
            return web.Response(status=401)

        if self.server.IDreviewID(data["testNumber"]):
            return web.Response(status=200)
        else:
            return web.Response(status=404)

    def setUpRoutes(self, router):
        # router.add_routes(self.local_route_table)
        # But see above: doesn't work with auth deco
        router.add_get("/ID/progress", self.IDprogressCount)
        router.add_get("/ID/classlist", self.IDgetClasslist)
        router.add_get("/ID/predictions", self.IDgetPredictions)
        router.add_get("/ID/tasks/complete", self.IDgetDoneTasks)
        router.add_get("/ID/images/{test}", self.IDgetImage)
        router.add_get("/ID/tasks/available", self.IDgetNextTask)
        router.add_patch("/ID/tasks/{task}", self.IDclaimThisTask)
        router.add_put("/ID/tasks/{task}", self.IDreturnIDdTask)
        router.add_delete("/ID/tasks/{task}", self.IDdidNotFinishTask)
        router.add_get("/ID/randomImage", self.IDgetRandomImage)
        router.add_delete("/ID/predictedID", self.IDdeletePredictions)
        router.add_patch("/ID/review", self.IDreviewID)
