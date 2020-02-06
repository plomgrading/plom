from aiohttp import web, MultipartWriter, MultipartReader
import os

# this allows us to import from ../resources
import sys

sys.path.append("..")
from resources.logIt import printLog


class IDHandler:
    def __init__(self, plomServer):
        printLog("IDH", "Starting identifier handler")
        self.server = plomServer

    # @routes.get("/ID/progress")
    async def IDprogressCount(self, request):
        printLog("IDH", "{} {}".format(request.method, request.rel_url))

        data = await request.json()
        if self.server.validate(data["user"], data["token"]):
            return web.json_response(self.server.IDprogressCount(), status=200)
        else:
            return web.Response(status=401)

    # @routes.get("/ID/classlist")
    async def IDgetClasslist(self, request):
        printLog("IDH", "{} {}".format(request.method, request.rel_url))
        data = await request.json()
        if self.server.validate(data["user"], data["token"]):
            if os.path.isfile("../resources/classlist.csv"):
                return web.FileResponse("../resources/classlist.csv", status=200)
            else:
                return web.Response(status=404)
        else:
            return web.Response(status=401)

    # @routes.get("/ID/predictions")
    async def IDgetPredictions(self, request):
        printLog("IDH", "{} {}".format(request.method, request.rel_url))
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
        printLog("IDH", "{} {}".format(request.method, request.rel_url))
        data = await request.json()
        if self.server.validate(data["user"], data["token"]):
            # return the completed list
            return web.json_response(
                self.server.IDgetDoneTasks(data["user"]), status=200
            )
        else:
            return web.Response(status=401)

    # @routes.get("/ID/images/{test}")
    async def IDgetImage(self, request):
        printLog("IDH", "{} {}".format(request.method, request.rel_url))
        data = await request.json()
        test = request.match_info["test"]

        if self.server.validate(data["user"], data["token"]):
            rmsg = self.server.IDgetImage(data["user"], test)
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

    # @routes.get("/ID/tasks/available")
    async def IDgetNextTask(self, request):
        printLog("IDH", "{} {}".format(request.method, request.rel_url))
        data = await request.json()
        if self.server.validate(data["user"], data["token"]):
            rmsg = self.server.IDgetNextTask()  # returns [True, code] or [False]
            if rmsg[0]:
                return web.json_response(rmsg[1], status=200)
            else:
                return web.Response(status=204)  # no papers left
        else:
            return web.Response(status=401)

    # @routes.patch("/ID/tasks/{task}")
    async def IDclaimThisTask(self, request):
        printLog("IDH", "{} {}".format(request.method, request.rel_url))
        data = await request.json()
        testNumber = request.match_info["task"]

        if self.server.validate(data["user"], data["token"]):
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
        else:
            return web.Response(status=401)

    # @routes.put("/ID/tasks/{task}")
    async def IDreturnIDdTask(self, request):
        printLog("IDH", "{} {}".format(request.method, request.rel_url))

        data = await request.json()
        testNumber = request.match_info["task"]
        if self.server.validate(data["user"], data["token"]):
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
        else:
            return web.Response(status=401)

    # @routes.delete("/ID/tasks/{task}")
    async def IDdidNotFinishTask(self, request):
        printLog("IDH", "{} {}".format(request.method, request.rel_url))
        data = await request.json()
        testNumber = request.match_info["task"]
        if self.server.validate(data["user"], data["token"]):
            self.server.IDdidNotFinish(data["user"], testNumber)
            return web.json_response(status=200)
        else:
            return web.Response(status=401)

    # @routes.get("/ID/randomImage")
    async def IDgetRandomImage(self, request):
        printLog("IDH", "{} {}".format(request.method, request.rel_url))
        data = await request.json()
        if (
            self.server.validate(data["user"], data["token"])
            and data["user"] == "manager"
        ):
            rmsg = self.server.IDgetRandomImage()
            print("Appending file {}".format(rmsg))
            with MultipartWriter("images") as mpwriter:
                for fn in rmsg[1:]:
                    if os.path.isfile(fn):
                        mpwriter.append(open(fn, "rb"))
                    else:
                        return web.Response(status=404)
                return web.Response(body=mpwriter, status=200)
        else:
            return web.Response(status=401)  # not authorised at all

    async def IDdeletePredictions(self, request):
        printLog("IDH", "{} {}".format(request.method, request.rel_url))
        data = await request.json()
        if (
            self.server.validate(data["user"], data["token"])
            and data["user"] == "manager"
        ):
            return web.json_response(self.server.IDdeletePredictions(), status=200)
        else:
            return web.Response(status=401)

    # @routes.patch("/ID/review")
    async def IDreviewID(self, request):
        printLog("IDH", "{} {}".format(request.method, request.rel_url))
        data = await request.json()
        if self.server.validate(data["user"], data["token"]):
            if self.server.IDreviewID(data["testNumber"]):
                return web.Response(status=200)
            else:
                return web.Response(status=404)
        else:
            return web.Response(status=401)

    def setUpRoutes(self, router):
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
