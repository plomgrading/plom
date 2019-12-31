from aiohttp import web, MultipartWriter, MultipartReader
import os


class MarkHandler:
    def __init__(self, plomServer):
        self.server = plomServer

    # @routes.get("/MK/maxMark")
    async def MgetQuestionMark(self, request):
        data = await request.json()
        if self.server.validate(data["user"], data["token"]):
            rmsg = self.server.MgetQuestionMax(data["q"], data["v"])
            if rmsg[0]:
                return web.json_response(rmsg[1], status=200)
            elif rmsg[1] == "QE":
                # pg out of range
                return web.Response(
                    text="Question out of range - please check before trying again.",
                    status=416,
                )
            elif rmsg[1] == "VE":
                # version our of range
                return web.Response(
                    text="Version out of range - please check before trying again.",
                    status=416,
                )
        else:
            return web.Response(status=401)

    # @routes.get("/MK/progress")
    async def MprogressCount(self, request):
        data = await request.json()
        if self.server.validate(data["user"], data["token"]):
            return web.json_response(
                self.server.MprogressCount(data["q"], data["v"]), status=200
            )
        else:
            return web.Response(status=401)

    # @routes.get("/MK/tasks/complete")
    async def MgetDoneTasks(self, request):
        data = await request.json()
        if self.server.validate(data["user"], data["token"]):
            # return the completed list
            return web.json_response(
                self.server.MgetDoneTasks(data["user"], data["q"], data["v"]),
                status=200,
            )
        else:
            return web.Response(status=401)

    # @routes.get("/MK/tasks/available")
    async def MgetNextTask(self, request):
        data = await request.json()
        if self.server.validate(data["user"], data["token"]):
            rmsg = self.server.MgetNextTask(data["q"], data["v"])
            # returns [True, task] or [False]
            if rmsg[0]:
                return web.json_response(rmsg[1], status=200)
            else:
                return web.Response(status=204)  # no papers left
        else:
            return web.Response(status=401)

    # @routes.get("/MK/latex")
    async def MlatexFragment(self, request):
        data = await request.json()
        if self.server.validate(data["user"], data["token"]):
            rmsg = self.server.MlatexFragment(data["user"], data["fragment"])
            if rmsg[0]:  # user allowed access - returns [true, fname]
                return web.FileResponse(rmsg[1], status=200)
            else:
                return web.Response(status=406)  # a latex error
        else:
            return web.Response(status=401)  # not authorised at all

    # @routes.patch("/MK/tasks/{task}")
    async def MclaimThisTask(self, request):
        data = await request.json()
        task = request.match_info["task"]
        if self.server.validate(data["user"], data["token"]):
            rmesg = self.server.MclaimThisTask(data["user"], task)
            if rmesg[0]:  # return [True, tag, filename1, filename2,...]
                with MultipartWriter("imageAndTags") as mpwriter:
                    mpwriter.append(rmesg[1])  # append tags as raw text.
                    for fn in rmesg[2:]:
                        mpwriter.append(open(fn, "rb"))
                return web.Response(body=mpwriter, status=200)
            else:
                return web.Response(status=204)  # that task already taken.
        else:
            return web.Response(status=401)

    # @routes.delete("/MK/tasks/{task}")
    async def MdidNotFinishTask(self, request):
        data = await request.json()
        task = request.match_info["task"]
        if self.server.validate(data["user"], data["token"]):
            self.server.MdidNotFinish(data["user"], task)
            return web.json_response(status=200)
        else:
            return web.Response(status=401)

    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    # @routes.get("/MK/images/{task}")
    # async def MrequestImages(request):
    #     data = await request.json()
    #     task = request.match_info["task"]
    #     if self.server.validate(data["user"], data["token"]):
    #         rmsg = self.server.MrequestImages(data["user"], task)
    #         # returns either [True, fname] or [True, fname, aname, plomdat] or [False, error]
    #         if rmsg[0]:  # user allowed access - returns [true, fname]
    #             with MultipartWriter("imageAnImageAndPlom") as mpwriter:
    #                 mpwriter.append(open(rmsg[1], "rb"))
    #                 if len(rmsg) == 4:
    #                     mpwriter.append(open(rmsg[2], "rb"))
    #                     mpwriter.append(open(rmsg[3], "rb"))
    #             return web.Response(body=mpwriter, status=200)
    #         else:
    #             return web.Response(status=409)  # someone else has that image
    #     else:
    #         return web.Response(status=401)  # not authorised at all
    #
    #
    # @routes.get("/MK/originalImage/{task}")
    # async def MrequestOriginalImage(request):
    #     data = await request.json()
    #     task = request.match_info["task"]
    #     if self.server.validate(data["user"], data["token"]):
    #         rmsg = self.server.MrequestOriginalImage(task)
    #         # returns either [True, fname] or [False]
    #         if rmsg[0]:  # user allowed access - returns [true, fname]
    #             return web.FileResponse(rmsg[1], status=200)
    #         else:
    #             return web.Response(status=204)  # no content there
    #     else:
    #         return web.Response(status=401)  # not authorised at all
    #
    #
    # @routes.put("/MK/tasks/{task}")
    # async def MreturnMarkedTask(request):
    #     task = request.match_info["task"]
    #     # the put will be in 3 parts - use multipart reader
    #     # in order we expect those 3 parts - [parameters (inc comments), image, plom-file]
    #     reader = MultipartReader.from_response(request)
    #     part0 = await reader.next()
    #     if part0 is None:  # weird error
    #         return web.Response(status=406)  # should have sent 3 parts
    #     param = await part0.json()
    #     comments = param["comments"]
    #
    #     # image file
    #     part1 = await reader.next()
    #     if part1 is None:  # weird error
    #         return web.Response(status=406)  # should have sent 3 parts
    #     image = await part1.read()
    #
    #     # plom file
    #     part2 = await reader.next()
    #     if part2 is None:  # weird error
    #         return web.Response(status=406)  # should have sent 3 parts
    #     plomdat = await part2.read()
    #
    #     if self.server.validate(param["user"], param["token"]):
    #         rmsg = self.server.MreturnMarkedTask(
    #             param["user"],
    #             task,
    #             int(param["pg"]),
    #             int(param["ver"]),
    #             int(param["score"]),
    #             image,
    #             plomdat,
    #             comments,
    #             int(param["mtime"]),
    #             param["tags"],
    #         )
    #         # rmsg = either [True, numDone, numTotal] or [False] if error.
    #         if rmsg[0]:
    #             return web.json_response([rmsg[1], rmsg[2]], status=200)
    #         else:
    #             return web.Response(status=400)  # some sort of error with image file
    #     else:
    #         return web.Response(status=401)  # not authorised at all
    #
    #
    # @routes.patch("/MK/tags/{task}")
    # async def MsetTag(request):
    #     task = request.match_info["task"]
    #     data = await request.json()
    #     if self.server.validate(data["user"], data["token"]):
    #         rmsg = self.server.MsetTag(data["user"], task, data["tags"])
    #         if rmsg:
    #             return web.Response(status=200)
    #         else:
    #             return web.Response(status=409)  # this is not your task
    #     else:
    #         return web.Response(status=401)  # not authorised at all
    #
    #
    # @routes.get("/MK/whole/{number}")
    # async def MrequestWholePaper(request):
    #     data = await request.json()
    #     number = request.match_info["number"]
    #     if self.server.validate(data["user"], data["token"]):
    #         rmesg = self.server.MrequestWholePaper(data["user"], number)
    #         if rmesg[0]:  # return [True, [filenames]] or [False]
    #             with MultipartWriter("imageAndTags") as mpwriter:
    #                 for fn in rmesg[1]:
    #                     mpwriter.append(open(fn, "rb"))
    #             return web.Response(body=mpwriter, status=200)
    #         else:
    #             return web.Response(status=409)  # not yours
    #     else:
    #         return web.Response(status=401)

    def setUpRoutes(self, router):
        router.add_get("/MK/maxMark", self.MgetQuestionMark)
        router.add_get("/MK/progress", self.MprogressCount)
        router.add_get("/MK/tasks/complete", self.MgetDoneTasks)
        router.add_get("/MK/tasks/available", self.MgetNextTask)
        router.add_get("/MK/latex", self.MlatexFragment)
        router.add_patch("/MK/tasks/{task}", self.MclaimThisTask)
        router.add_delete("/MK/tasks/{task}", self.MdidNotFinishTask)
