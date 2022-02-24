# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2019-2020 Andrew Rechnitzer
# Copyright (C) 2020-2022 Colin B. Macdonald
# Copyright (C) 2020 Vala Vakilian

from aiohttp import web, MultipartWriter, MultipartReader

from plom import undo_json_packing_of_version_map
from .routeutils import authenticate_by_token_required_fields
from .routeutils import validate_required_fields, log_request, log


class UploadHandler:
    def __init__(self, plomServer):
        self.server = plomServer

    async def doesBundleExist(self, request):
        """Returns whether given bundle/md5sum known to database

        Checks both bundle's name and md5sum
        * neither = no matching bundle, return [False, None]
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
        * If bundle matches either 'name' or 'md5sum' then return [False, reason] - this shouldn't happen if scanner working correctly.
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

    async def listBundles(self, request):
        """Returns a list of dicts of bundles in the database."""
        data = await request.json()
        if not validate_required_fields(data, ["user", "token"]):
            return web.Response(status=400)
        if not self.server.validate(data["user"], data["token"]):
            return web.Response(status=401)
        if not data["user"] in ["scanner", "manager"]:
            return web.Response(status=401)
        rval = self.server.listBundles()
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
        code = request.match_info["tpv"]  # noqa: F841

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
        """A homework page is self-scanned, known student, and known(-ish) questions.

        Typically the page is without QR codes.  The uploader knows what
        student it belongs to and what question(s).  The order within the
        question is somewhat known too, at least within its upload bundle.

        Args:
            request (aiohttp.web_request.Request): a multipart thing
                The ``questions`` field is a list of questions.

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
                "questions",
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
            param["questions"],
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
        # code = request.match_info["tpv"]

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

    async def replaceMissingDNMPage(self, request):
        data = await request.json()
        if not validate_required_fields(data, ["user", "token", "test", "page"]):
            return web.Response(status=400)
        if not self.server.validate(data["user"], data["token"]):
            return web.Response(status=401)
        if not data["user"] == "manager":
            return web.Response(status=401)

        rval = self.server.replaceMissingDNMPage(data["test"], data["page"])
        if rval[0]:
            return web.json_response(rval, status=200)  # all fine
        else:
            if rval[1] == "owners":  # [False, "owners", owner_list]
                return web.json_response(rval[2], status=409)
            else:
                return web.Response(status=404)  # page not found at all

    async def replaceMissingIDPage(self, request):
        data = await request.json()
        if not validate_required_fields(data, ["user", "token", "test"]):
            return web.Response(status=400)
        if not self.server.validate(data["user"], data["token"]):
            return web.Response(status=401)
        if not data["user"] == "manager":
            return web.Response(status=401)

        rval = self.server.replaceMissingIDPage(data["test"])
        if rval[0]:
            return web.json_response(rval, status=200)  # all fine
        else:
            if rval[1] == "owners":  # [False, "owners", owner_list]
                return web.json_response(rval[2], status=409)
            elif rval[1] == "unknown":
                return web.Response(status=410)
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
                # that question already has pages
                return web.Response(status=405)
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

    async def removeSinglePage(self, request):
        """Remove the page (as described by its name) and reset any tasks that involve that page.
        This tries to be as minimal as possible - so, for example, if a tpage is removed, then
        the question that included that page goes back on the todo-list (after a newpage is uploaded),
        but at the same time if a TA has used a copy of that page in the annotation of another
        question, that group is also reset and goes back on the todo-list."""

        data = await request.json()
        if not validate_required_fields(
            data,
            ["user", "token", "test", "page_name"],
        ):
            return web.Response(status=400)
        if not self.server.validate(data["user"], data["token"]):
            return web.Response(status=401)
        if not data["user"] == "manager":
            return web.Response(status=401)

        rval = self.server.removeSinglePage(data["test"], data["page_name"])
        if rval[0]:
            return web.json_response(rval, status=200)  # all fine
        else:
            if rval[1] == "owners":  # [False, "owners", owner_list]
                return web.json_response(rval[2], status=409)
            elif rval[1] == "unknown":  # [False, "unknown"]
                raise web.HTTPGone(reason="Cannot find that page.")
            elif rval[1] == "invalid":
                raise web.HTTPNotAcceptable(reason="Page name is invalid")
            else:
                raise web.HTTPBadRequest()

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

        ok, filenames = self.server.getQuestionImages(data["test"], data["question"])
        if not ok:
            # 2nd return value is error message in this case
            raise web.HTTPNotFound(reason=filenames)
        # suboptimal but safe: read bytes instead of append(fh) (Issue #1877)
        with MultipartWriter("images") as mpwriter:
            mpwriter.append(str(len(filenames)))
            for f in filenames:
                with open(f, "rb") as fh:
                    b = fh.read()
                mpwriter.append(b)
            return web.Response(body=mpwriter, status=200)

    # @routes.get("/admin/testImages")
    @authenticate_by_token_required_fields(["user", "test"])
    def getAllTestImages(self, data, request):
        if not data["user"] == "manager":
            return web.Response(status=401)

        ok, filenames = self.server.getAllTestImages(data["test"])
        if not ok:
            # 2nd return value is error message in this case
            raise web.HTTPNotFound(reason=filenames)
        # suboptimal but safe: read bytes instead of append(fh) (Issue #1877)
        with MultipartWriter("images") as mpwriter:
            mpwriter.append(str(len(filenames)))
            for f in filenames:
                with open(f, "rb") as fh:
                    b = fh.read()
                mpwriter.append(b)
            return web.Response(body=mpwriter, status=200)

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
        if not rmsg[0]:
            return web.Response(status=404)  # couldn't find that test/question
        with MultipartWriter("images") as mpwriter:
            mpwriter.append("{}".format(rmsg[1]))
            mpwriter.append("{}".format(rmsg[2]))
            if len(rmsg) > 3:  # append the image.
                assert len(rmsg) == 4
                with open(rmsg[3], "rb") as fh:
                    b = fh.read()
                mpwriter.append(b)
            return web.Response(body=mpwriter, status=200)

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
        """The unknown page is moved to the indicated tpage.

        The minimal set of groups are reset when this happens
        - namely the group containing the new tpage.

        args:
            request (aiohttp.web_request.Request): This has the usual "user"
                and "token" fields but also:
                    fileName (str): identifies the UnknownPage.
                    test (str): paper number to map onto (int passed as str).
                    page (str): page number (again, an int)
                    rotation (str): an integer, presumably a multiple of 90
                        0, 90, -90, 180, 270, etc.  TODO: needs an overhaul
                        to support immutable server side images (with in-DB
                        metadata rotations (Issue #1879).

        returns:
            web.Response: 200 if all went well.  400 for incorrect fields,
                401 for authentication, or 403 is not manager.  406 if we
                can't do the move due to users logged in.  409 in other
                such as test number or page number do not exist.
        """
        data = await request.json()
        if not validate_required_fields(
            data, ["user", "token", "fileName", "test", "page", "rotation"]
        ):
            return web.Response(status=400)
        if not self.server.validate(data["user"], data["token"]):
            return web.Response(status=401)
        if not data["user"] == "manager":
            raise web.HTTPForbidden(reason="I can only speak to the manager")

        status, code, msg = self.server.unknownToTestPage(
            data["fileName"], data["test"], data["page"], data["rotation"]
        )
        if status:
            assert msg is None
            return web.json_response(code, status=200)  # all fine
        if code == "owners":
            log.warn(msg)
            raise web.HTTPNotAcceptable(reason=msg)
        if code == "notfound":
            log.warn(msg)
            raise web.HTTPConflict(reason=msg)
        log.warn("Unexpected situation: %s", msg)
        raise web.HTTPBadRequest(reason=f"Unexpected situation: {msg}")

    async def unknownToHWPage(self, request):
        """Map an unknown page onto one or more HomeworkPages.

        args:
            request (aiohttp.web_request.Request): This has the usual "user"
                and "token" fields but also:
                    fileName (str): identifies the UnknownPage.
                    test (str): paper number to map onto (int passed as str).
                    questions (list): question numbers, ints.
                    rotation (str): an integer, presumably a multiple of 90
                        0, 90, -90, 180, 270, etc.  TODO: needs an overhaul
                        to support immutable server side images (with in-DB
                        metadata rotations (Issue #1879).

        returns:
            web.Response: 200 if all went well.  400 for incorrect fields,
                401 for authentication, or 403 is not manager.  406 if we
                can't do the move due to users logged in.  409 if paper
                number or question number do not exist (e.g., out of range).
        """
        data = await request.json()
        if not validate_required_fields(
            data, ["user", "token", "fileName", "test", "questions", "rotation"]
        ):
            return web.Response(status=400)
        if not self.server.validate(data["user"], data["token"]):
            return web.Response(status=401)
        if not data["user"] == "manager":
            raise web.HTTPForbidden(reason="I can only speak to the manager")

        status, code, msg = self.server.unknownToHWPage(
            data["fileName"], data["test"], data["questions"], data["rotation"]
        )
        if status:
            return web.Response(status=200)  # all fine
        if code == "owners":
            log.warn(msg)
            raise web.HTTPNotAcceptable(reason=msg)
        if code == "notfound":
            log.warn(msg)
            raise web.HTTPConflict(reason=msg)
        log.warn("Unexpected situation: %s", msg)
        raise web.HTTPBadRequest(reason=f"Unexpected situation: {msg}")

    async def unknownToExtraPage(self, request):
        """Map an unknown page onto one or more extra pages.

        args:
            request (aiohttp.web_request.Request): This has the usual "user"
                and "token" fields but also:
                    fileName (str): identifies the UnknownPage.
                    test (str): paper number to map onto (int passed as str).
                    questions (list): question numbers, a list of integers.
                    rotation (str): an integer, presumably a multiple of 90
                        0, 90, -90, 180, 270, etc.  TODO: needs an overhaul
                        to support immutable server side images (with in-DB
                        metadata rotations (Issue #1879).

        returns:
            web.Response: 200 if all went well.  400 for incorrect fields,
                401 for authentication, or 403 is not manager.  406 if we
                can't do the move due to users logged in.   409 if paper
                number or question number do not exist (e.g., out of range).
                Also, 409 if one or more questions not scanned (so cannot
                attach extra page).  This is important as otherwise we can
                bypass the scanned mechanism and a test of only extra pages
                could be overlooked (not graded nor returned).
        """
        data = await request.json()
        if not validate_required_fields(
            data, ["user", "token", "fileName", "test", "questions", "rotation"]
        ):
            return web.Response(status=400)
        if not self.server.validate(data["user"], data["token"]):
            return web.Response(status=401)
        if not data["user"] == "manager":
            raise web.HTTPForbidden(reason="I can only speak to the manager")

        status, code, msg = self.server.unknownToExtraPage(
            data["fileName"], data["test"], data["questions"], data["rotation"]
        )
        if status:
            return web.Response(status=200)
        if code == "owners":
            log.warn(msg)
            raise web.HTTPNotAcceptable(reason=msg)
        if code == "notfound":
            log.warn(msg)
            raise web.HTTPConflict(reason=msg)
        if code == "unscanned":
            log.warn(msg)
            raise web.HTTPConflict(reason=msg)
        log.warn("Unexpected situation: %s", msg)
        raise web.HTTPBadRequest(reason=f"Unexpected situation: {msg}")

    async def collidingToTestPage(self, request):
        """The group containing the tpage is reset when it is replaced.
        At the same time, any annotation that involved the old tpage is reset.
        """
        data = await request.json()
        if not validate_required_fields(
            data, ["user", "token", "fileName", "test", "page", "version"]
        ):
            return web.Response(status=400)
        if not self.server.validate(data["user"], data["token"]):
            return web.Response(status=401)
        if not data["user"] == "manager":
            raise web.HTTPForbidden(reason="I can only speak to the manager")

        status, code, msg = self.server.collidingToTestPage(
            data["fileName"], data["test"], data["page"], data["version"]
        )
        if status:
            return web.Response(status=200)  # all fine
        if code == "owners":
            log.warn(msg)
            raise web.HTTPNotAcceptable(reason=msg)
        if code == "notfound":
            log.warn(msg)
            raise web.HTTPConflict(reason=msg)
        log.warn("Unexpected situation: %s", msg)
        raise web.HTTPBadRequest(reason=f"Unexpected situation: {msg}")

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

    @authenticate_by_token_required_fields(["user", "version_map"])
    def populateExamDatabase(self, data, request):
        """Instruct the server to generate paper data in the database.

        TODO: maybe the api call should just be for one row of the database.
        """
        if not data["user"] == "manager":
            raise web.HTTPForbidden(reason="Not manager")
        spec = self.server.testSpec
        if not spec:
            raise web.HTTPBadRequest(reason="Server has no spec; cannot populate DB")

        # TODO: talking to DB directly is not design we use elsewhere: call helper?
        from plom.db import buildExamDatabaseFromSpec

        if len(data["version_map"]) == 0:
            vmap = None
        else:
            vmap = undo_json_packing_of_version_map(data["version_map"])

        try:
            r, summary = buildExamDatabaseFromSpec(spec, self.server.DB, vmap)
        except ValueError:
            raise web.HTTPConflict(
                reason="Database already present: not overwriting"
            ) from None
        if r:
            return web.Response(text=summary, status=200)
        else:
            raise web.HTTPInternalServerError(text=summary)

    @authenticate_by_token_required_fields([])
    def getGlobalPageVersionMap(self, data, request):
        """Get the mapping between page number and version for all tests.

        Returns:
            dict: dict of dicts, keyed first by paper index then by page
                number.  Both keys are strings b/c of json limitations;
                you may need to iterate and convert back to int.  Fails
                with 409 if the version map database has not been built
                yet.

        Note: careful not to confuse this with /admin/questionVersionMap
            which is much more likely what you are looking for.
        """
        spec = self.server.testSpec
        if not spec:
            raise web.HTTPNotFound(reason="Server has no spec so no version map")
        vers = {}
        for paper_idx in range(1, spec["numberToProduce"] + 1):
            ver = self.server.DB.getPageVersions(paper_idx)
            if not ver:
                _msg = "There is no version map: have you built the database?"
                log.warn(_msg)
                raise web.HTTPConflict(reason=_msg)
            vers[paper_idx] = ver
        return web.json_response(vers, status=200)

    @authenticate_by_token_required_fields([])
    def getQuestionVersionMap(self, data, request):
        """Get the mapping between questions and version for one test.

        Returns:
            dict: keyed by question number.  Note keys will be strings b/c
                of json limitations; you may need to convert back to int.
                Fails with 409 if there is no version map.
        """
        paper_idx = request.match_info["papernum"]
        vers = self.server.DB.getQuestionVersions(paper_idx)
        if not vers:
            _msg = f"paper {paper_idx} does not (yet?) have a version map"
            log.warn(_msg)
            raise web.HTTPConflict(reason=_msg)
        return web.json_response(vers, status=200)

    @authenticate_by_token_required_fields([])
    def getGlobalQuestionVersionMap(self, data, request):
        """Get the mapping between question and version for all tests.

        Returns:
            dict: dict of dicts, keyed first by paper index then by
                question number.  Both keys will become strings b/c of
                json limitations; you may need to convert back to int.
                Fails with 404/409 if there is no version map: 404 if
                the server has no spec and 409 if the server has a spec
                but the version map database has not been built yet.
        """
        spec = self.server.testSpec
        if not spec:
            raise web.HTTPNotFound(reason="Server has no spec so no version map")
        vers = {}
        for paper_idx in range(1, spec["numberToProduce"] + 1):
            ver = self.server.DB.getQuestionVersions(paper_idx)
            if not ver:
                _msg = "There is no version map: have you built the database?"
                log.warn(_msg)
                raise web.HTTPConflict(reason=_msg)
            vers[paper_idx] = ver
        return web.json_response(vers, status=200)

    # Some more bundle things

    @authenticate_by_token_required_fields(["user", "filename"])
    def getBundleFromImage(self, data, request):
        """Returns the name of the bundle that contains the given image.

        If DB can't find the file then returns HTTPGone error.
        If not manager, then raise an HTTPUnauthorized error.
        """
        if not data["user"] == "manager":
            return web.HTTPUnauthorized(reason="You are not manager")
        rval = self.server.getBundleFromImage(data["filename"])
        if rval[0]:
            return web.json_response(rval[1], status=200)  # all fine
        else:  # no such bundle
            raise web.HTTPGone(reason="Cannot find bundle.")

    @authenticate_by_token_required_fields(["user", "bundle"])
    def getImagesInBundle(self, data, request):
        """Returns list of images inside the given bundle. Each image is returned as a triple of (filename, md5sum and bundle_order). The list is ordered by the bundle_order.

        If DB does not contain bundle of that name a 410-error returned.
        If user is not manager or scanner then a HTTPUnauthorised error raised.
        """
        if not data["user"] in ("manager", "scanner"):
            raise web.HTTPUnauthorized(
                reason="only manager and scanner can access bundle info"
            )
        rval = self.server.getImagesInBundle(data["bundle"])
        if rval[0]:
            return web.json_response(rval[1], status=200)  # all fine
        else:
            raise web.HTTPGone(reason="Cannot find bundle.")

    async def getPageFromBundle(self, request):
        """Get the image at position bundle_order from the bundle with the given name. This is used (for example) to examine neighbouring images inside a given bundle.

        If DB does not contain a bundle of that name or the bundle does not contain an image at that order then raise an HTTPGone error.
        """
        data = await request.json()
        if not validate_required_fields(
            data, ["user", "token", "bundle_name", "bundle_order"]
        ):
            return web.Response(status=400)
        if not self.server.validate(data["user"], data["token"]):
            return web.Response(status=401)
        if not data["user"] == "manager":
            raise web.HTTPUnauthorized(
                reason="only manager can access images by bundle position."
            )

        rval = self.server.getPageFromBundle(data["bundle_name"], data["bundle_order"])
        if rval[0]:
            return web.FileResponse(rval[1], status=200)  # all fine
        else:
            raise web.HTTPGone(reason="Cannot find image or bundle.")

    def setUpRoutes(self, router):
        router.add_get("/admin/bundle", self.doesBundleExist)
        router.add_put("/admin/bundle", self.createNewBundle)
        router.add_get("/admin/bundle/list", self.listBundles)
        router.add_get("/admin/sidToTest", self.sidToTest)
        router.add_put("/admin/testPages/{tpv}", self.uploadTestPage)
        router.add_put("/admin/hwPages", self.uploadHWPage)
        router.add_put("/admin/unknownPages", self.uploadUnknownPage)
        router.add_put("/admin/collidingPages/{tpv}", self.uploadCollidingPage)
        router.add_put("/admin/missingTestPage", self.replaceMissingTestPage)
        router.add_put("/admin/missingDNMPage", self.replaceMissingDNMPage)
        router.add_put("/admin/missingIDPage", self.replaceMissingIDPage)
        router.add_put("/admin/missingHWQuestion", self.replaceMissingHWQuestion)
        router.add_delete("/admin/scannedPages", self.removeAllScannedPages)
        router.add_delete("/admin/singlePage", self.removeSinglePage)
        router.add_get("/admin/scannedTPage", self.getTPageImage)
        router.add_get("/admin/scannedHWPage", self.getHWPageImage)
        router.add_get("/admin/scannedEXPage", self.getEXPageImage)
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
        router.add_put("/admin/populateDB", self.populateExamDatabase)
        router.add_get("/admin/pageVersionMap", self.getGlobalPageVersionMap)
        router.add_get(
            "/admin/questionVersionMap/{papernum}", self.getQuestionVersionMap
        )
        router.add_get("/admin/questionVersionMap", self.getGlobalQuestionVersionMap)
        router.add_get("/admin/bundleFromImage", self.getBundleFromImage)
        router.add_get("/admin/imagesInBundle", self.getImagesInBundle)
        router.add_get("/admin/bundlePage", self.getPageFromBundle)
