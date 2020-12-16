# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2019-2020 Andrew Rechnitzer
# Copyright (C) 2020 Colin B. Macdonald
# Copyright (C) 2020 Vala Vakilian

from aiohttp import web, MultipartWriter, MultipartReader

from .routeutils import authenticate_by_token, authenticate_by_token_required_fields
from .routeutils import validate_required_fields, log_request, log


class UploadHandler:
    def __init__(self, plomServer):
        self.server = plomServer

    async def doesBundleExist(self, request):
        """Returns whether given bundle/md5sum known to database

        Checks both bundle's name and md5sum
        * neither = no matching bundle, return [False]
        * name but not md5 = return [True, 'name'] - user is trying to upload different bundles with same name.
        * md5 but not name = return [True, 'md5sum'] - user is trying to same bundle with different names.
        * both match = return [True, 'both'] - user could be retrying
          after network failure (for example) or uploading unknown or
          colliding pages.
        """
        data = await request.json()
        if not validate_required_fields(data, ["user", "token", "bundle", "md5sum"]):
            return web.Response(status=400)
        if not self.server.validate(data["user"], data["token"]):
            return web.Response(status=401)
        if not data["user"] in ["scanner", "manager"]:
            return web.Response(status=401)
        rval = self.server.doesBundleExist(data["bundle"], data["md5sum"])
        return web.json_response(rval, status=200)  # all fine

    async def createNewBundle(self, request):
        """Try to create bundle with given name/md5sum.

        First check name / md5sum of bundle.
        * If bundle matches either 'name' or 'md5sum' then return [False, reason] - this shouldnt happen if scanner working correctly.
        * If bundle matches 'both' then return [True, skip_list] where skip_list = the page-orders from that bundle that are already in the system. The scan scripts will then skip those uploads.
        * If no such bundle return [True, []] - create the bundle and return an empty skip-list.

        Notes:
        * after declaring a bundle you may upload images to it.
        * uploading pages to an undeclared bundle is not allowed.
        * bundles traditionally correspond to one "pile" of physical
          papers scanned together.
        * there does not need to be one-to-one relationship betewen
          bundles and Exam Papers or Homework Papers.
        """
        log_request("createNewBundle", request)

        data = await request.json()
        if not validate_required_fields(data, ["user", "token", "bundle", "md5sum"]):
            return web.Response(status=400)
        if not self.server.validate(data["user"], data["token"]):
            return web.Response(status=401)
        if not data["user"] in ["scanner", "manager"]:
            return web.Response(status=401)
        rval = self.server.createNewBundle(data["bundle"], data["md5sum"])
        return web.json_response(rval, status=200)  # all fine

    async def sidToTest(self, request):
        """Match given student_id to a test-number.

        Returns
        * [True, test_number]
        * [False, 'Cannot find test with that student id']
        """
        data = await request.json()
        if not validate_required_fields(data, ["user", "token", "sid"]):
            return web.Response(status=400)
        if not self.server.validate(data["user"], data["token"]):
            return web.Response(status=401)
        if not data["user"] in ["scanner", "manager"]:
            return web.Response(status=401)
        rval = self.server.sidToTest(data["sid"])
        return web.json_response(rval, status=200)

    async def uploadTestPage(self, request):
        """A test page has known page, known paper number, usually QR-coded.

        Typically the page is QR coded, and thus we know precisely what
        paper number, what question and what page.  We may not know the
        student depending on whether it was prenamed or not.

        Args:
            request (aiohttp.web_request.Request)

        Returns:
            aiohttp.web_response.Response: JSON data directly from the
                database call.

        Note: this uses the `status=200` success return code for some
        kinds of failures: it simply returns whatever data the DB gave
        back as blob of json for the client to deal with.  Thus, this
        API call is not recommended outside of Plom.
        """
        reader = MultipartReader.from_response(request)

        part0 = await reader.next()  # should be parameters
        if part0 is None:  # weird error
            return web.Response(status=406)  # should have sent 3 parts
        param = await part0.json()

        if not validate_required_fields(
            param,
            [
                "user",
                "token",
                "test",
                "page",
                "version",
                "fileName",
                "md5sum",
                "bundle",
                "bundle_order",
            ],
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
            param["bundle"],
            param["bundle_order"],
        )
        # note 200 used here for errors too
        return web.json_response(rmsg, status=200)

    async def uploadHWPage(self, request):
        """A homework page is self-scanned, known student, and known questions.

        Typically the page is without QR codes.  The uploader knows what
        student it belongs to and what question(s).  The order within the
        question is somewhat known too, at least within its upload bundle.

        Args:
            request (aiohttp.web_request.Request)

        Returns:
            aiohttp.web_response.Response: JSON data directly from the
                database call.

        The requests data has a `question` field, which can be a scalar
        or a list of questions we wish to upload too.  Maybe the scalar
        is deprecated?
        TODO: force it to always be a list?

        Note: this uses the `status=200` success return code for some
        kinds of failures: it simply returns whatever data the DB gave
        back as blob of json for the client to deal with.  Thus, this
        API call is not recommended outside of Plom.
        """
        reader = MultipartReader.from_response(request)

        part0 = await reader.next()  # should be parameters
        if part0 is None:  # weird error
            return web.Response(status=406)  # should have sent 3 parts
        param = await part0.json()

        if not validate_required_fields(
            param,
            [
                "user",
                "token",
                "sid",
                "question",
                "order",
                "fileName",
                "md5sum",
                "bundle",
                "bundle_order",
            ],
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
            param["bundle"],
            param["bundle_order"],
        )
        # note 200 used here for errors too
        return web.json_response(rmsg, status=200)

    async def uploadLPage(self, request):
        """A loose page is self-scanned, known student, but unknown question.

        Typically the page is without QR codes.  The uploader knows what
        student it belongs to but not what question.

        DEPRECATED? Perhaps on its way to deprecation if HW Pages become
        more general in the future.

        Args:
            request (aiohttp.web_request.Request)

        Returns:
            aiohttp.web_response.Response: JSON data directly from the
                database call.

        Note: this uses the `status=200` success return code for some
        kinds of failures: it simply returns whatever data the DB gave
        back as blob of json for the client to deal with.  Thus, this
        API call is not recommended outside of Plom.
        """
        reader = MultipartReader.from_response(request)

        part0 = await reader.next()  # should be parameters
        if part0 is None:  # weird error
            return web.Response(status=406)  # should have sent 3 parts
        param = await part0.json()

        if not validate_required_fields(
            param,
            [
                "user",
                "token",
                "sid",
                "order",
                "fileName",
                "md5sum",
                "bundle",
                "bundle_order",
            ],
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
        rmsg = self.server.addLPage(
            param["sid"],
            param["order"],
            param["fileName"],
            image,
            param["md5sum"],
            param["bundle"],
            param["bundle_order"],
        )
        # note 200 used here for errors too
        return web.json_response(rmsg, status=200)

    async def uploadUnknownPage(self, request):
        reader = MultipartReader.from_response(request)

        part0 = await reader.next()  # should be parameters
        if part0 is None:  # weird error
            return web.Response(status=406)  # should have sent 3 parts
        param = await part0.json()

        if not validate_required_fields(
            param,
            ["user", "token", "fileName", "order", "md5sum", "bundle", "bundle_order"],
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
        rmsg = self.server.addUnknownPage(
            param["fileName"],
            image,
            param["order"],
            param["md5sum"],
            param["bundle"],
            param["bundle_order"],
        )
        # note 200 used here for errors too
        return web.json_response(rmsg, status=200)

    async def uploadCollidingPage(self, request):
        reader = MultipartReader.from_response(request)

        part0 = await reader.next()  # should be parameters
        if part0 is None:  # weird error
            return web.Response(status=406)  # should have sent 2 parts
        param = await part0.json()

        if not validate_required_fields(
            param,
            [
                "user",
                "token",
                "fileName",
                "md5sum",
                "test",
                "page",
                "version",
                "bundle",
                "bundle_order",
            ],
        ):
            return web.Response(status=400)
        if not self.server.validate(param["user"], param["token"]):
            return web.Response(status=401)
        # TODO - restrict to manager only.
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
            param["bundle"],
            param["bundle_order"],
        )
        # note 200 used here for errors too
        return web.json_response(rmsg, status=200)

    async def replaceMissingTestPage(self, request):
        data = await request.json()
        if not validate_required_fields(
            data, ["user", "token", "test", "page", "version"]
        ):
            return web.Response(status=400)
        if not self.server.validate(data["user"], data["token"]):
            return web.Response(status=401)
        if not data["user"] == "manager":
            return web.Response(status=401)

        rval = self.server.replaceMissingTestPage(
            data["test"], data["page"], data["version"]
        )
        if rval[0]:
            return web.json_response(rval, status=200)  # all fine
        else:
            if rval[1] == "owners":  # [False, "owners", owner_list]
                return web.json_response(rval[2], status=409)
            else:
                return web.Response(status=404)  # page not found at all

    async def replaceMissingHWQuestion(self, request):
        # can replace either by SID-lookup or test-number
        data = await request.json()
        if not validate_required_fields(
            data, ["user", "token", "sid", "test", "question"]
        ):
            return web.Response(status=400)
        if not self.server.validate(data["user"], data["token"]):
            return web.Response(status=401)
        if data["user"] != "manager" and data["user"] != "scanner":
            return web.Response(status=401)

        rval = self.server.replaceMissingHWQuestion(
            data["sid"], data["test"], data["question"]
        )
        if rval[0]:
            return web.json_response(rval, status=200)  # all fine
        else:
            if rval[1] == "owners":
                return web.json_response(rval[2], status=409)
            elif rval[1] == "present":
                return web.Response(status=405)  # that question already has pages
            else:
                return web.Response(status=404)  # page not found at all

    async def removeAllScannedPages(self, request):
        data = await request.json()
        if not validate_required_fields(
            data,
            [
                "user",
                "token",
                "test",
            ],
        ):
            return web.Response(status=400)
        if not self.server.validate(data["user"], data["token"]):
            return web.Response(status=401)
        if not data["user"] == "manager":
            return web.Response(status=401)

        rval = self.server.removeAllScannedPages(
            data["test"],
        )
        if rval[0]:
            return web.json_response(rval, status=200)  # all fine
        else:
            if rval[1] == "owners":  # [False, "owners", owner_list]
                return web.json_response(rval[2], status=409)
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
        if not validate_required_fields(
            data, ["user", "token", "test", "page", "version"]
        ):
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
        if not validate_required_fields(
            data, ["user", "token", "test", "question", "order"]
        ):
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

    async def getEXPageImage(self, request):
        data = await request.json()
        if not validate_required_fields(
            data, ["user", "token", "test", "question", "order"]
        ):
            return web.Response(status=400)
        if not self.server.validate(data["user"], data["token"]):
            return web.Response(status=401)
        if not data["user"] == "manager":
            return web.Response(status=401)

        rval = self.server.getEXPageImage(data["test"], data["question"], data["order"])
        if rval[0]:
            return web.FileResponse(rval[1], status=200)  # all fine
        else:
            return web.Response(status=404)

    async def getLPageImage(self, request):
        data = await request.json()
        if not validate_required_fields(data, ["user", "token", "test", "order"]):
            return web.Response(status=400)
        if not self.server.validate(data["user"], data["token"]):
            return web.Response(status=401)
        if not data["user"] == "manager":
            return web.Response(status=401)

        rval = self.server.getLPageImage(data["test"], data["order"])
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
            # insert number of parts [n, fn.1,fn.2,...fn.n]
            with MultipartWriter("images") as mpwriter:
                mpwriter.append(str(len(rmsg) - 1))
                for fn in rmsg[1:]:
                    mpwriter.append(open(fn, "rb"))
            return web.Response(body=mpwriter, status=200)
        else:
            return web.Response(status=404)  # couldnt find that test/question

    # @routes.get("/admin/testImages")
    @authenticate_by_token_required_fields(["user", "test"])
    def getAllTestImages(self, data, request):
        if not data["user"] == "manager":
            return web.Response(status=401)

        rmsg = self.server.getAllTestImages(data["test"])
        # returns either [True, fname1,fname2,..,fname.n] or [False, error]
        if rmsg[0]:
            # insert number of parts [n, fn.1,fn.2,...fn.n]
            with MultipartWriter("images") as mpwriter:
                mpwriter.append(str(len(rmsg) - 1))
                for fn in rmsg[1:]:
                    if fn == "":
                        mpwriter.append("")
                    else:
                        mpwriter.append(open(fn, "rb"))
            return web.Response(body=mpwriter, status=200)
        else:
            return web.Response(status=404)  # couldnt find that test/question

    async def checkTPage(self, request):
        data = await request.json()
        if not validate_required_fields(data, ["user", "token", "test", "page"]):
            return web.Response(status=400)
        if not self.server.validate(data["user"], data["token"]):
            return web.Response(status=401)
        if not data["user"] == "manager":
            return web.Response(status=401)

        rmsg = self.server.checkTPage(data["test"], data["page"])
        # returns either [True, "collision", version, fname], [True, "scanned", version] or [False]
        if rmsg[0]:
            with MultipartWriter("images") as mpwriter:
                mpwriter.append("{}".format(rmsg[1]))  # append "collision" or "scanned"
                mpwriter.append("{}".format(rmsg[2]))  # append "version"
                if len(rmsg) == 4:  # append the image.
                    mpwriter.append(open(rmsg[3], "rb"))
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
            if rval[1] == "owners":  # [False, "owners", owner_list]
                return web.json_response(rval[2], status=409)
            else:
                return web.Response(status=404)

    async def unknownToHWPage(self, request):
        data = await request.json()
        if not validate_required_fields(
            data, ["user", "token", "fileName", "test", "question", "rotation"]
        ):
            return web.Response(status=400)
        if not self.server.validate(data["user"], data["token"]):
            return web.Response(status=401)
        if not data["user"] == "manager":
            return web.Response(status=401)

        rval = self.server.unknownToHWPage(
            data["fileName"], data["test"], data["question"], data["rotation"]
        )
        if rval[0]:
            return web.Response(status=200)  # all fine
        else:
            if rval[1] == "owners":  # [False, "owners", owner_list]
                return web.json_response(rval[2], status=409)
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
        )  # returns [True], or [False, reason]
        if rval[0]:
            return web.Response(status=200)  # all fine
        else:
            if rval[1] == "owners":  # [False, "owners", owner_list]
                return web.json_response(rval[2], status=409)
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
            if rval[1] == "owners":  # [False, "owners", owner_list]
                return web.json_response(rval[2], status=409)
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
        """Trigger any updates that are appropriate after some uploads.

        This is probably similar to :py:meth:`processTUploads`
        """
        data = await request.json()
        if not validate_required_fields(data, ["user", "token"]):
            return web.Response(status=400)
        if not self.server.validate(data["user"], data["token"]):
            return web.Response(status=401)
        if data["user"] != "manager" and data["user"] != "scanner":
            return web.Response(status=401)

        update_count = self.server.processHWUploads()
        return web.json_response(update_count, status=200)

    async def processLUploads(self, request):
        """Trigger any updates that are appropriate after some uploads.

        This is probably similar to :py:meth:`processTUploads`
        """
        data = await request.json()
        if not validate_required_fields(data, ["user", "token"]):
            return web.Response(status=400)
        if not self.server.validate(data["user"], data["token"]):
            return web.Response(status=401)
        if data["user"] != "manager" and data["user"] != "scanner":
            return web.Response(status=401)

        update_count = self.server.processLUploads()
        return web.json_response(update_count, status=200)

    async def processTUploads(self, request):
        """Trigger any updates that are appropriate after some uploads.

        If we upload a bunch of pages to the server, the server will
        typically keep those in some sort of "staging" state where, for
        example, they are not given to marking clients.  This is b/c it
        will be distruptive to clients to have pages added to questions.
        To "release" a these recent uploads, we make this API call.

        Notes:
          * its ok to upload to a bundle after calling this (worse case,
            some client work will be invalidated or tagged to check).
          * its ok to call this repeatedly.
          * its not necessarily or useful to call this after uploading
            Unknown Pages or Colliding Pages: those will need to be
            dealt with in the Manager tool (e.g., added them to a
            Paper) at which time similar triggers will occur.

        Returns:
            aiohttp.web.Response: with status code as below.

        Status codes:
            200 OK: action was taken, report numer of Papers updated.
            401 Unauthorized: invalid credientials.
            403 Forbidden: only "manager"/"scanner" allowed to do this.
        """
        data = await request.json()
        if not validate_required_fields(data, ["user", "token"]):
            return web.Response(status=400)
        if not self.server.validate(data["user"], data["token"]):
            return web.Response(status=401)
        if data["user"] != "manager" and data["user"] != "scanner":
            return web.Response(status=403)

        update_count = self.server.processTUploads()
        return web.json_response(update_count, status=200)

    @authenticate_by_token_required_fields(["user"])
    def populateExamDatabase(self, data, request):
        """Instruct the server to generate paper data in the database.

        TODO: maybe the api call should just be for one row of the database.

        TODO: or maybe we can pass the page-to-version mapping to this?
        """
        if not data["user"] == "manager":
            return web.Response(status=400)  # malformed request.

        from plom.db import buildExamDatabaseFromSpec

        # TODO this is not the design we have elsewhere, should call helper function
        try:
            r, summary = buildExamDatabaseFromSpec(self.server.testSpec, self.server.DB)
        except ValueError:
            raise web.HTTPConflict(
                reason="Database already present: not overwriting"
            ) from None
        if r:
            return web.Response(text=summary, status=200)
        else:
            raise web.HTTPInternalServerError(text=summary)

    # TODO: would be nice to use @authenticate_by_token, see comments in routeutils.py
    @authenticate_by_token_required_fields([])
    def getPageVersionMap(self, data, request):
        """Get the mapping between page number and version for one test.

        Returns:
            dict: keyed by page number.  Note keys are strings b/c of
                json limitations; you may want to convert back to int.
        """
        spec = self.server.testSpec
        paper_idx = request.match_info["papernum"]
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
                you may need to iterate and convert back to int.  Fails
                with 500 Internal Server Error if a test does not exist.
        """
        spec = self.server.testSpec
        vers = {}
        for paper_idx in range(1, spec["numberToProduce"] + 1):
            ver = self.server.DB.getPageVersions(paper_idx)
            if not ver:
                return web.Response(status=500)
            vers[paper_idx] = ver
        # JSON converts int keys to strings, we'll fix this at the far end
        # return web.json_response(str(pickle.dumps(vers)), status=200)
        return web.json_response(vers, status=200)

    # @route.put("/admin/pdf_produced/{t}")
    @authenticate_by_token_required_fields(["user"])
    def notify_pdf_of_paper_produced(self, data, request):
        """Inform server that a PDF for this paper has been produced.

        This is to be called one-at-a-time for each paper.  If this is a
        bottleneck we could consider adding a "bulk" version.

        Note that the file itself is not uploaded to the server: we're
        just merely creating a record that such a file exists somewhere.

        TODO: pass in md5sum too and if its unchanged no need to
        complain about conflict, just quietly return 200.
        TODO: implement force as mentioned below.

        Inputs:
            t (int?, str?): part of URL that specifies the paper number.
            user (str): who's calling?  A field of the request.
            force (bool): force production even if paper already exists.
            md5sum (str): md5sum of the file that was produced.

        Returns:
            aiohttp.web.Response: with status code as below.

        Status codes:
            200 OK: the info was recorded.
            400 Bad Request: only "manager" is allowed to do this.
            401 Unauthorized: invalid credientials.
            404 Not Found: paper number is outside valid range.
            409 Conflict: this paper has already been produced, so its
                unusual to be making it again. Maybe try `force=True`.
        """
        if not data["user"] == "manager":
            return web.Response(status=400)
        # force_flag = request.match_info["force"]
        paper_idx = request.match_info["papernum"]
        try:
            self.server.DB.produceTest(paper_idx)
        except IndexError:
            return web.Response(status=404)
        except ValueError:
            return web.Response(status=409)
        return web.Response(status=200)

    def setUpRoutes(self, router):
        router.add_get("/admin/bundle", self.doesBundleExist)
        router.add_put("/admin/bundle", self.createNewBundle)
        router.add_get("/admin/sidToTest", self.sidToTest)
        router.add_put("/admin/testPages/{tpv}", self.uploadTestPage)
        router.add_put("/admin/hwPages", self.uploadHWPage)
        router.add_put("/admin/lPages", self.uploadLPage)
        router.add_put("/admin/unknownPages", self.uploadUnknownPage)
        router.add_put("/admin/collidingPages/{tpv}", self.uploadCollidingPage)
        router.add_put("/admin/missingTestPage", self.replaceMissingTestPage)
        router.add_put("/admin/missingHWQuestion", self.replaceMissingHWQuestion)
        router.add_delete("/admin/scannedPages", self.removeAllScannedPages)
        router.add_get("/admin/scannedTPage", self.getTPageImage)
        router.add_get("/admin/scannedHWPage", self.getHWPageImage)
        router.add_get("/admin/scannedEXPage", self.getEXPageImage)
        router.add_get("/admin/scannedLPage", self.getLPageImage)
        router.add_get("/admin/unknownPageNames", self.getUnknownPageNames)
        router.add_get("/admin/discardNames", self.getDiscardNames)
        router.add_get("/admin/collidingPageNames", self.getCollidingPageNames)
        router.add_get("/admin/unknownImage", self.getUnknownImage)
        router.add_get("/admin/discardImage", self.getDiscardImage)
        router.add_get("/admin/collidingImage", self.getCollidingImage)
        router.add_get("/admin/questionImages", self.getQuestionImages)
        router.add_get("/admin/testImages", self.getAllTestImages)
        router.add_get("/admin/checkTPage", self.checkTPage)
        router.add_delete("/admin/unknownImage", self.removeUnknownImage)
        router.add_delete("/admin/collidingImage", self.removeCollidingImage)
        router.add_put("/admin/unknownToTestPage", self.unknownToTestPage)
        router.add_put("/admin/unknownToHWPage", self.unknownToHWPage)
        router.add_put("/admin/unknownToExtraPage", self.unknownToExtraPage)
        router.add_put("/admin/collidingToTestPage", self.collidingToTestPage)
        router.add_put("/admin/discardToUnknown", self.discardToUnknown)
        router.add_put("/admin/hwPagesUploaded", self.processHWUploads)
        router.add_put("/admin/loosePagesUploaded", self.processLUploads)
        router.add_put("/admin/testPagesUploaded", self.processTUploads)
        router.add_put("/admin/populateDB", self.populateExamDatabase)
        router.add_get("/admin/pageVersionMap/{papernum}", self.getPageVersionMap)
        router.add_get("/admin/pageVersionMap", self.getGlobalPageVersionMap)
        router.add_put(
            "/admin/pdf_produced/{papernum}", self.notify_pdf_of_paper_produced
        )
