from aiohttp import web, MultipartWriter, MultipartReader

from .routeutils import authenticate_by_token, authenticate_by_token_required_fields
from .routeutils import validate_required_fields, log


class UploadHandler:
    def __init__(self, plomServer):
        self.server = plomServer

    async def uploadTestPage(self, request):
        reader = MultipartReader.from_response(request)

        part0 = await reader.next()  # should be parameters
        if part0 is None:  # weird error
            return web.Response(status=406)  # should have sent 3 parts
        param = await part0.json()

        if not validate_required_fields(
            param, ["user", "token", "test", "page", "version", "fileName", "md5sum"]
        ):
            return web.Response(status=400)
        if not self.server.validate(param["user"], param["token"]):
            return web.Response(status=401)
        if not param["user"] in ("manager", "scanner"):
            return web.Response(status=401)

        # TODO: unused, we should ensure this matches the data
        # TODO: or why bother passing those in to param?
        code = request.match_info["tpv"]

        part1 = await reader.next()  # should be the image file
        if part1 is None:  # weird error
            return web.Response(status=406)  # should have sent 3 parts
        image = await part1.read()
        # file it away.
        rmsg = self.server.addTestPage(
            param["test"],
            param["page"],
            param["version"],
            param["fileName"],
            image,
            param["md5sum"],
        )
        return web.json_response(rmsg, status=200)  # all good

    async def uploadHWPage(self, request):
        reader = MultipartReader.from_response(request)

        part0 = await reader.next()  # should be parameters
        if part0 is None:  # weird error
            return web.Response(status=406)  # should have sent 3 parts
        param = await part0.json()

        if not validate_required_fields(
            param, ["user", "token", "sid", "question", "order", "fileName", "md5sum"]
        ):
            return web.Response(status=400)
        if not self.server.validate(param["user"], param["token"]):
            return web.Response(status=401)
        if not param["user"] in ("manager", "scanner"):
            return web.Response(status=401)

        part1 = await reader.next()  # should be the image file
        if part1 is None:  # weird error
            return web.Response(status=406)  # should have sent 3 parts
        image = await part1.read()
        # file it away.
        rmsg = self.server.addHWPage(
            param["sid"],
            param["question"],
            param["order"],
            param["fileName"],
            image,
            param["md5sum"],
        )
        return web.json_response(rmsg, status=200)  # all good

    async def uploadXPage(self, request):
        reader = MultipartReader.from_response(request)

        part0 = await reader.next()  # should be parameters
        if part0 is None:  # weird error
            return web.Response(status=406)  # should have sent 3 parts
        param = await part0.json()

        if not validate_required_fields(
            param, ["user", "token", "sid", "order", "fileName", "md5sum"]
        ):
            return web.Response(status=400)
        if not self.server.validate(param["user"], param["token"]):
            return web.Response(status=401)
        if not param["user"] in ("manager", "scanner"):
            return web.Response(status=401)

        part1 = await reader.next()  # should be the image file
        if part1 is None:  # weird error
            return web.Response(status=406)  # should have sent 3 parts
        image = await part1.read()
        # file it away.
        rmsg = self.server.addXPage(
            param["sid"], param["order"], param["fileName"], image, param["md5sum"],
        )
        return web.json_response(rmsg, status=200)  # all good

    async def uploadUnknownPage(self, request):
        reader = MultipartReader.from_response(request)

        part0 = await reader.next()  # should be parameters
        if part0 is None:  # weird error
            return web.Response(status=406)  # should have sent 3 parts
        param = await part0.json()

        if not validate_required_fields(param, ["user", "token", "fileName", "md5sum"]):
            return web.Response(status=400)
        if not self.server.validate(param["user"], param["token"]):
            return web.Response(status=401)
        if not param["user"] in ("manager", "scanner"):
            return web.Response(status=401)

        part1 = await reader.next()  # should be the image file
        if part1 is None:  # weird error
            return web.Response(status=406)  # should have sent 3 parts
        image = await part1.read()
        # file it away.
        rmsg = self.server.addUnknownPage(param["fileName"], image, param["md5sum"],)
        return web.json_response(rmsg, status=200)  # all good

    async def uploadCollidingPage(self, request):
        reader = MultipartReader.from_response(request)

        part0 = await reader.next()  # should be parameters
        if part0 is None:  # weird error
            return web.Response(status=406)  # should have sent 2 parts
        param = await part0.json()

        if not validate_required_fields(
            param, ["user", "token", "fileName", "md5sum", "test", "page", "version"]
        ):
            return web.Response(status=400)
        if not self.server.validate(param["user"], param["token"]):
            return web.Response(status=401)
        if not param["user"] in ("manager", "scanner"):
            return web.Response(status=401)

        # TODO: unused, we should ensure this matches the data
        code = request.match_info["tpv"]

        part1 = await reader.next()  # should be the image file
        if part1 is None:  # weird error
            return web.Response(status=406)  # should have sent 2 parts
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

    async def replaceMissingTestPage(self, request):
        data = await request.json()
        if not validate_required_fields(data, ["user", "token", "test", "page", "version"]):
            return web.Response(status=400)
        if not self.server.validate(data["user"], data["token"]):
            return web.Response(status=401)
        if not data["user"] == "manager":
            return web.Response(status=401)

        # TODO: unused, we should ensure this matches the data
        code = request.match_info["tpv"]

        rval = self.server.replaceMissingTestPage(
            data["test"], data["page"], data["version"]
        )
        if rval[0]:
            return web.json_response(rval, status=200)  # all fine
        else:
            return web.Response(status=404)  # page not found at all

    async def replaceMissingHWQuestion(self, request):
        data = await request.json()
        if not validate_required_fields(data, ["user", "token", "sid", "question"]):
            return web.Response(status=400)
        if not self.server.validate(data["user"], data["token"]):
            return web.Response(status=401)
        if data["user"] != "manager" and data["user"] != "scanner":
            return web.Response(status=401)

        rval = self.server.replaceMissingHWQuestion(data["sid"], data["question"])
        if rval[0]:
            return web.json_response(rval, status=200)  # all fine
        elif rval[1]:
            return web.Response(status=409)  # that question already has pages
        else:
            return web.Response(status=404)  # page not found at all

    async def removeScannedPage(self, request):
        data = await request.json()
        if not validate_required_fields(data, ["user", "token", "test", "page", "version"]):
            return web.Response(status=400)
        if not self.server.validate(data["user"], data["token"]):
            return web.Response(status=401)
        if not data["user"] == "manager":
            return web.Response(status=401)

        # TODO: unused, we should ensure this matches the data
        code = request.match_info["tpv"]

        rval = self.server.removeScannedPage(
            data["test"], data["page"], data["version"]
        )
        if rval[0]:
            return web.json_response(rval, status=200)  # all fine
        else:
            return web.Response(status=404)  # page not found at all

    async def getUnknownPageNames(self, request):
        data = await request.json()
        if not validate_required_fields(data, ["user", "token"]):
            return web.Response(status=400)
        if not self.server.validate(data["user"], data["token"]):
            return web.Response(status=401)
        if not data["user"] == "manager":
            return web.Response(status=401)

        rval = self.server.getUnknownPageNames()
        return web.json_response(rval, status=200)  # all fine

    async def getDiscardNames(self, request):
        data = await request.json()
        if not validate_required_fields(data, ["user", "token"]):
            return web.Response(status=400)
        if not self.server.validate(data["user"], data["token"]):
            return web.Response(status=401)
        if not data["user"] == "manager":
            return web.Response(status=401)

        rval = self.server.getDiscardNames()
        return web.json_response(rval, status=200)  # all fine

    async def getCollidingPageNames(self, request):
        data = await request.json()
        if not validate_required_fields(data, ["user", "token"]):
            return web.Response(status=400)
        if not self.server.validate(data["user"], data["token"]):
            return web.Response(status=401)
        if not data["user"] == "manager":
            return web.Response(status=401)

        rval = self.server.getCollidingPageNames()
        return web.json_response(rval, status=200)  # all fine

    async def getTPageImage(self, request):
        data = await request.json()
        if not validate_required_fields(data, ["user", "token", "test", "page", "version"]):
            return web.Response(status=400)
        if not self.server.validate(data["user"], data["token"]):
            return web.Response(status=401)
        if not data["user"] == "manager":
            return web.Response(status=401)

        rval = self.server.getTPageImage(data["test"], data["page"], data["version"])
        if rval[0]:
            return web.FileResponse(rval[1], status=200)  # all fine
        else:
            return web.Response(status=404)

    async def getHWPageImage(self, request):  # should this use version too?
        data = await request.json()
        if not validate_required_fields(data, ["user", "token", "test", "question", "order"]):
            return web.Response(status=400)
        if not self.server.validate(data["user"], data["token"]):
            return web.Response(status=401)
        if not data["user"] == "manager":
            return web.Response(status=401)

        rval = self.server.getHWPageImage(data["test"], data["question"], data["order"])
        if rval[0]:
            return web.FileResponse(rval[1], status=200)  # all fine
        else:
            return web.Response(status=404)

    async def getXPageImage(self, request):
        data = await request.json()
        if not validate_required_fields(data, ["user", "token", "test", "order"]):
            return web.Response(status=400)
        if not self.server.validate(data["user"], data["token"]):
            return web.Response(status=401)
        if not data["user"] == "manager":
            return web.Response(status=401)

        rval = self.server.getXPageImage(data["test"], data["order"])
        if rval[0]:
            return web.FileResponse(rval[1], status=200)  # all fine
        else:
            return web.Response(status=404)

    async def getUnknownImage(self, request):
        data = await request.json()
        if not validate_required_fields(data, ["user", "token", "fileName"]):
            return web.Response(status=400)
        if not self.server.validate(data["user"], data["token"]):
            return web.Response(status=401)
        if not data["user"] == "manager":
            return web.Response(status=401)

        rval = self.server.getUnknownImage(data["fileName"])
        if rval[0]:
            return web.FileResponse(rval[1], status=200)  # all fine
        else:
            return web.Response(status=404)

    async def getDiscardImage(self, request):
        data = await request.json()
        if not validate_required_fields(data, ["user", "token", "fileName"]):
            return web.Response(status=400)
        if not self.server.validate(data["user"], data["token"]):
            return web.Response(status=401)
        if not data["user"] == "manager":
            return web.Response(status=401)

        rval = self.server.getDiscardImage(data["fileName"])
        if rval[0]:
            return web.FileResponse(rval[1], status=200)  # all fine
        else:
            return web.Response(status=404)

    async def getCollidingImage(self, request):
        data = await request.json()
        if not validate_required_fields(data, ["user", "token", "fileName"]):
            return web.Response(status=400)
        if not self.server.validate(data["user"], data["token"]):
            return web.Response(status=401)
        if not data["user"] == "manager":
            return web.Response(status=401)

        rval = self.server.getCollidingImage(data["fileName"])
        if rval[0]:
            return web.FileResponse(rval[1], status=200)  # all fine
        else:
            return web.Response(status=404)

    # @route.get("/admin/questionImages")
    @authenticate_by_token_required_fields(["user", "test", "question"])
    def getQuestionImages(self, data, request):
        if not data["user"] == "manager":
            return web.Response(status=401)

        rmsg = self.server.getQuestionImages(data["test"], data["question"])
        # returns either [True, fname1,fname2,..,fname.n] or [False, error]
        if rmsg[0]:
            with MultipartWriter("images") as mpwriter:
                for fn in rmsg[1:]:
                    mpwriter.append(open(fn, "rb"))
            return web.Response(body=mpwriter, status=200)
        else:
            return web.Response(status=404)  # couldnt find that test/question

    # @routes.get("/admin/testImages")
    @authenticate_by_token_required_fields(["user", "test"])
    def getTestImages(self, data, request):
        if not data["user"] == "manager":
            return web.Response(status=401)

        rmsg = self.server.getTestImages(data["test"])
        # returns either [True, fname1,fname2,..,fname.n] or [False, error]
        if rmsg[0]:
            with MultipartWriter("images") as mpwriter:
                for fn in rmsg[1:]:
                    if fn == "":
                        mpwriter.append("")
                    else:
                        mpwriter.append(open(fn, "rb"))
            return web.Response(body=mpwriter, status=200)
        else:
            return web.Response(status=404)  # couldnt find that test/question

    async def checkPage(self, request):
        data = await request.json()
        if not validate_required_fields(data, ["user", "token", "test", "page", "images"]):
            return web.Response(status=400)
        if not self.server.validate(data["user"], data["token"]):
            return web.Response(status=401)
        if not data["user"] == "manager":
            return web.Response(status=401)

        rmsg = self.server.checkPage(data["test"], data["page"])
        # returns either [True, version, fname], [True, version] or [False]
        if rmsg[0]:
            with MultipartWriter("images") as mpwriter:
                mpwriter.append("{}".format(rmsg[1]))
                if len(rmsg) == 3:
                    mpwriter.append(open(rmsg[2], "rb"))
            return web.Response(body=mpwriter, status=200)
        else:
            return web.Response(status=404)  # couldnt find that test/question

    async def removeUnknownImage(self, request):
        data = await request.json()
        if not validate_required_fields(data, ["user", "token", "fileName"]):
            return web.Response(status=400)
        if not self.server.validate(data["user"], data["token"]):
            return web.Response(status=401)
        if not data["user"] == "manager":
            return web.Response(status=401)

        rval = self.server.removeUnknownImage(data["fileName"])
        if rval[0]:
            return web.Response(status=200)  # all fine
        else:
            return web.Response(status=404)

    async def removeCollidingImage(self, request):
        data = await request.json()
        if not validate_required_fields(data, ["user", "token", "fileName"]):
            return web.Response(status=400)
        if not self.server.validate(data["user"], data["token"]):
            return web.Response(status=401)
        if not data["user"] == "manager":
            return web.Response(status=401)

        rval = self.server.removeCollidingImage(data["fileName"])
        if rval[0]:
            return web.Response(status=200)  # all fine
        else:
            return web.Response(status=404)

    async def unknownToTestPage(self, request):
        data = await request.json()
        if not validate_required_fields(
            data, ["user", "token", "fileName", "test", "page", "rotation"]
        ):
            return web.Response(status=400)
        if not self.server.validate(data["user"], data["token"]):
            return web.Response(status=401)
        if not data["user"] == "manager":
            return web.Response(status=401)

        rval = self.server.unknownToTestPage(
            data["fileName"], data["test"], data["page"], data["rotation"]
        )
        if rval[0]:
            return web.json_response(rval[1], status=200)  # all fine
        else:
            return web.Response(status=404)

    async def unknownToExtraPage(self, request):
        data = await request.json()
        if not validate_required_fields(
            data, ["user", "token", "fileName", "test", "question", "rotation"]
        ):
            return web.Response(status=400)
        if not self.server.validate(data["user"], data["token"]):
            return web.Response(status=401)
        if not data["user"] == "manager":
            return web.Response(status=401)

        rval = self.server.unknownToExtraPage(
            data["fileName"], data["test"], data["question"], data["rotation"]
        )
        if rval[0]:
            return web.Response(status=200)  # all fine
        else:
            return web.Response(status=404)

    async def collidingToTestPage(self, request):
        data = await request.json()
        if not validate_required_fields(
            data, ["user", "token", "fileName", "test", "page", "version"]
        ):
            return web.Response(status=400)
        if not self.server.validate(data["user"], data["token"]):
            return web.Response(status=401)
        if not data["user"] == "manager":
            return web.Response(status=401)

        rval = self.server.collidingToTestPage(
            data["fileName"], data["test"], data["page"], data["version"]
        )
        if rval[0]:
            return web.Response(status=200)  # all fine
        else:
            return web.Response(status=404)

    async def discardToUnknown(self, request):
        data = await request.json()
        if not validate_required_fields(data, ["user", "token", "fileName"]):
            return web.Response(status=400)
        if not self.server.validate(data["user"], data["token"]):
            return web.Response(status=401)
        if not data["user"] == "manager":
            return web.Response(status=401)

        rval = self.server.discardToUnknown(data["fileName"])
        if rval[0]:
            return web.Response(status=200)  # all fine
        else:
            return web.Response(status=404)

    async def processHWUploads(self, request):
        data = await request.json()
        if not validate_required_fields(data, ["user", "token"]):
            return web.Response(status=400)
        if not self.server.validate(data["user"], data["token"]):
            return web.Response(status=401)
        if data["user"] != "manager" and data["user"] != "scanner":
            return web.Response(status=401)

        rval = self.server.processHWUploads()
        return web.json_response(
            rval[1], status=200
        )  # all fine - report number of tests updated

    async def processTUploads(self, request):
        data = await request.json()
        if not validate_required_fields(data, ["user", "token"]):
            return web.Response(status=400)
        if not self.server.validate(data["user"], data["token"]):
            return web.Response(status=401)
        if data["user"] != "manager" and data["user"] != "scanner":
            return web.Response(status=401)

        rval = self.server.processTUploads()
        return web.json_response(
            rval[1], status=200
        )  # all fine - report number of tests updated

    @authenticate_by_token_required_fields(["user"])
    def populateExamDatabase(self, data, request):
        """TODO summary.

        TODO: maybe the api call should just be for one row of the database.

        TODO: or maybe we can pass the page-to-version mapping to this?

        TODO: plom-build does error out, but I'd prefer an explicit nonempty test.
        """
        if not data["user"] == "manager":
            return web.Response(status=400)  # malformed request.

        # TODO: should ensure its empty, or require some "force" flag otherwise?
        #force_flag = request.match_info["force"]

        from plom.db import buildExamDatabaseFromSpec
        # TODO this is not the design we have elsewhere, should call helper function
        r, status = buildExamDatabaseFromSpec(self.server.testSpec, self.server.DB)
        if r:
            return web.json_response([r, status], status=200)  # all is fine
        else:
            return web.Response(status=404)

    # TODO: why can't I use authenticate_by_token decorator?
    @authenticate_by_token_required_fields([])
    def getPageVersionMap(self, data, request):
        """Get the mapping between page number and version for one test.

        Returns:
            dict: keyed by page number.  Note keys are strings b/c of
                json limitations; you may want to convert back to int.
        """
        spec = self.server.testSpec
        paper_idx = request.match_info["t"]
        ver = self.server.DB.getPageVersions(paper_idx)
        if ver:
            return web.json_response(ver, status=200)
        else:
            return web.Response(status=404)

    @authenticate_by_token_required_fields([])
    def getGlobalPageVersionMap(self, data, request):
        """Get the mapping between page number and version for all tests.

        Returns:
            dict: dict of dicts, keyed first by paper index then by page
                number.  Both keys are strings b/c of json limitations;
                you may need to iterate and convert back to int.
        """
        spec = self.server.testSpec
        vers = {}
        for paper_idx in range(1, spec["numberToProduce"] + 1):
            ver = self.server.DB.getPageVersions(paper_idx)
            #if not ver:
            #    TODO return 500
            vers[paper_idx] = ver
        # TODO: json converts int keys to strings
        #import pickle
        #return web.json_response(str(pickle.dumps(vers)), status=200)
        return web.json_response(vers, status=200)

    def setUpRoutes(self, router):
        router.add_put("/admin/testPages/{tpv}", self.uploadTestPage)
        router.add_put("/admin/hwPages", self.uploadHWPage)
        router.add_put("/admin/xPages", self.uploadXPage)
        router.add_put("/admin/unknownPages", self.uploadUnknownPage)
        router.add_put("/admin/collidingPages/{tpv}", self.uploadCollidingPage)
        router.add_put("/admin/missingTestPage/{tpv}", self.replaceMissingTestPage)
        router.add_put("/admin/missingHWQuestion", self.replaceMissingHWQuestion)
        router.add_delete("/admin/scannedPage/{tpv}", self.removeScannedPage)
        router.add_get("/admin/scannedTPage", self.getTPageImage)
        router.add_get("/admin/scannedHWPage", self.getHWPageImage)
        router.add_get("/admin/scannedXPage", self.getXPageImage)
        router.add_get("/admin/unknownPageNames", self.getUnknownPageNames)
        router.add_get("/admin/discardNames", self.getDiscardNames)
        router.add_get("/admin/collidingPageNames", self.getCollidingPageNames)
        router.add_get("/admin/unknownImage", self.getUnknownImage)
        router.add_get("/admin/discardImage", self.getDiscardImage)
        router.add_get("/admin/collidingImage", self.getCollidingImage)
        router.add_get("/admin/questionImages", self.getQuestionImages)
        router.add_get("/admin/testImages", self.getTestImages)
        router.add_get("/admin/checkPage", self.checkPage)
        router.add_delete("/admin/unknownImage", self.removeUnknownImage)
        router.add_delete("/admin/collidingImage", self.removeCollidingImage)
        router.add_put("/admin/unknownToTestPage", self.unknownToTestPage)
        router.add_put("/admin/unknownToExtraPage", self.unknownToExtraPage)
        router.add_put("/admin/collidingToTestPage", self.collidingToTestPage)
        router.add_put("/admin/discardToUnknown", self.discardToUnknown)
        router.add_put("/admin/hwPagesUploaded", self.processHWUploads)
        router.add_put("/admin/testPagesUploaded", self.processHWUploads)
        router.add_put("/DEV/admin/populateDB", self.populateExamDatabase)
        router.add_get("/DEV/admin/pageVersionMap/{t}", self.getPageVersionMap)
        router.add_get("/DEV/admin/pageVersionMap", self.getGlobalPageVersionMap)
