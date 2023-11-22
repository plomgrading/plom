# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2019-2020 Andrew Rechnitzer
# Copyright (C) 2020-2023 Colin B. Macdonald
# Copyright (C) 2020 Vala Vakilian

from aiohttp import web, MultipartWriter, MultipartReader
import csv

from plom import specdir
from plom import undo_json_packing_of_version_map
from .routeutils import authenticate_by_token_required_fields
from .routeutils import validate_required_fields, log_request, log
from .routeutils import readonly_admin, write_admin


class UploadHandler:
    """The Upload Handler interfaces between the HTTP API and the server itself.

    These routes handle requests related to uploading of images, such
    as at scanning time.  Also included are various administrative actions
    such as shifting UnknownPages into ExtraPages.

    Various miscellaneous routes about initialising and configuring the
    server seem to have landed here as well.
    """

    def __init__(self, plomServer):
        self.server = plomServer

    async def doesBundleExist(self, request):
        """Returns whether given bundle/md5sum known to database.

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

        .. note::

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

    @authenticate_by_token_required_fields(["user", "sid"])
    def sidToTest(self, data, request):
        """Match given student_id to a test-number.

        Returns:
            list: depend on success or failure, gives:

            * ``[True, test_number]``
            * ``[False, "Cannot find test with that student id"]``

        The test number could be b/c the paper is IDed.  Or it could be a
        prediction (a confident one, currently "prename").
        """
        if not data["user"] in ("scanner", "manager"):
            return web.HTTPUnauthorized(reason='must be "scanner" or "manager"')
        rval = self.server.sidToTest(data["sid"])
        return web.json_response(rval)

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

        # load up the classlist to get the student-name from the sid.
        # TODO - move classlist stuff into database.
        student_name = None
        try:
            with open(specdir / "classlist.csv", "r") as f:
                reader = csv.DictReader(f)
                # extract the student-name based on the ID.
                for row in reader:
                    if str(row["id"]) == str(param["sid"]):
                        student_name = row["name"]
                        break
        except FileNotFoundError:
            raise web.HTTPNotFound(reason="classlist not found")
        if student_name is None:
            raise web.HTTPNotFound(
                reason="cannot find student with that ID in classlist"
            )

        # file it away.
        rmsg = self.server.addHWPage(
            param["sid"],
            student_name,
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

    # @routes.put("/plom/admin/missingTestPage")
    @authenticate_by_token_required_fields(["test", "page", "version"])
    @write_admin
    def replaceMissingTestPage(self, data, request):
        """Replace a do-not-mark page with a server-generated placeholder.

        We will create the placeholder image.

        Args:
            ``test``, ``page``, and ``version`` in the data dict.

        Returns:
            200: on success, currently with some json diagnostics info.
            401/403: auth.
            404: page or test not found.
            409: conflict such as collision with image already in place
            or a repeated upload of the same placeholder.
            400: poorly formed or otherwise unexpected catchall.
        """
        ok, reason, X = self.server.replaceMissingTestPage(
            data["test"], data["page"], data["version"]
        )
        if ok:
            assert reason == "success"
            return web.json_response(X, status=200)
        if reason in ("testError", "pageError"):
            raise web.HTTPNotFound(reason=X)
        if reason == "duplicate":
            raise web.HTTPConflict(reason=X)
        if reason in "collision":
            # TODO: refactor `message_or_tuple`?
            msg = "Collision: " + str(X)
            raise web.HTTPConflict(reason=msg)
        # includes "bundleError" and anything unexpected
        msg = reason + ": " + str(X)
        raise web.HTTPBadRequest(reason=msg)

    # @routes.put("/plom/admin/missingDNMPage")
    @authenticate_by_token_required_fields(["test", "page"])
    @write_admin
    def replaceMissingDNMPage(self, data, request):
        """Replace a do-not-mark page with a server-generated placeholder.

        We will create the placeholder image.

        Args:
            ``test`` and ``page`` in the data dict.

        Returns:
            200: on success, currently with some json diagnostics info.
            401/403: auth.
            404: page or test not found.
            409: conflict such as collision with image already in place
            or a repeated upload of the same placeholder.
            400: poorly formed or otherwise unexpected catchall.
        """
        ok, reason, X = self.server.replaceMissingDNMPage(data["test"], data["page"])
        if ok:
            assert reason == "success"
            return web.json_response(X, status=200)
        if reason in ("testError", "pageError"):
            raise web.HTTPNotFound(reason=X)
        if reason == "duplicate":
            raise web.HTTPConflict(reason=X)
        if reason in "collision":
            # TODO: refactor `message_or_tuple`?
            msg = "Collision: " + str(X)
            raise web.HTTPConflict(reason=msg)
        # includes "bundleError" and anything unexpected
        msg = reason + ": " + str(X)
        raise web.HTTPBadRequest(reason=msg)

    # @routes.put("/plom/admin/missingDNMPage")
    @authenticate_by_token_required_fields(["test"])
    @write_admin
    def replaceMissingIDPage(self, data, request):
        """Replace a missing ID page a server-generated placeholder, for identified tests only.

        TODO: suspicious quality, needs work, Issue #2461.

        Args:
            ``test`` in the data dict.

        Returns:
            200: on success, currently with some json diagnostics info (?) but
            can also return 200 when HW already had an ID page (?)
            401/403: auth
            404: page or test not found
            410: paper not identified (e.g., not homework)
            400: poorly formed or otherwise unexpected catchall
        """
        rval = self.server.replaceMissingIDPage(data["test"])
        if rval[0]:
            return web.json_response(rval, status=200)  # all fine
        if rval[1] == "unknown":
            raise web.HTTPGone(
                reason=f'Cannot substitute ID page of test {data["test"]}'
                " because that paper is not identified"
            )
        if rval[1] == "hasonealready":
            raise web.HTTPGone(
                reason=f'Cannot substitute ID page of test {data["test"]}'
                " because that paper already has an ID page"
            )
        raise web.HTTPBadRequest(reason=f"Something has gone wrong: {str(rval)}")

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
            if rval[1] == "present":
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
            return web.Response(status=404)  # page not found at all

    # DELETE: /plom/admin/singlePage
    @authenticate_by_token_required_fields(["user", "test", "page_name"])
    @write_admin
    def removeSinglePage(self, data, request):
        """Remove the page (as described by its name) and reset any tasks that involve that page.

        This tries to be as minimal as possible - so, for example, if a tpage is removed, then
        the question that included that page goes back on the todo-list (after a newpage is uploaded),
        but at the same time if a TA has used a copy of that page in the annotation of another
        question, that group is also reset and goes back on the todo-list.
        """
        ok, code, msg = self.server.removeSinglePage(data["test"], data["page_name"])
        if ok:
            return web.json_response(msg, status=200)  # all fine
        if code == "unknown":
            raise web.HTTPConflict(reason=msg)
        elif code == "unscanned":
            raise web.HTTPGone(reason=msg)
        elif code == "invalid":
            raise web.HTTPNotAcceptable(reason=msg)
        else:
            raise web.HTTPBadRequest(reason=msg)

    async def getUnknownPages(self, request):
        data = await request.json()
        if not validate_required_fields(data, ["user", "token"]):
            return web.Response(status=400)
        if not self.server.validate(data["user"], data["token"]):
            return web.Response(status=401)
        if not data["user"] in ("scanner", "manager"):
            raise web.HTTPForbidden(reason="Only manager and scanner can use this")
        rval = self.server.getUnknownPages()
        return web.json_response(rval, status=200)

    async def getDiscardedPages(self, request):
        data = await request.json()
        if not validate_required_fields(data, ["user", "token"]):
            return web.Response(status=400)
        if not self.server.validate(data["user"], data["token"]):
            return web.Response(status=401)
        if data["user"] != "manager":
            raise web.HTTPForbidden(reason="I only speak to the manager")
        rval = self.server.getDiscardedPages()
        return web.json_response(rval, status=200)

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
            raise web.HTTPForbidden(reason="I want to speak to the manager")

        ok, val = self.server.getTPageImage(data["test"], data["page"], data["version"])
        if not ok:
            raise web.HTTPBadRequest(reason=val)  # TODO: was 404

        rownames = ("pagename", "md5", "orientation", "id", "server_path")
        pagedata = [{k: v for k, v in zip(rownames, val)}]
        return web.json_response(pagedata, status=200)

    async def getHWPageImage(self, request):  # should this use version too?
        data = await request.json()
        if not validate_required_fields(
            data, ["user", "token", "test", "question", "order"]
        ):
            return web.Response(status=400)
        if not self.server.validate(data["user"], data["token"]):
            return web.Response(status=401)
        if not data["user"] == "manager":
            raise web.HTTPForbidden(reason="I want to speak to the manager")

        ok, val = self.server.getHWPageImage(
            data["test"], data["question"], data["order"]
        )
        if not ok:
            raise web.HTTPBadRequest(reason=val)  # TODO: was 404
        rownames = ("pagename", "md5", "orientation", "id", "server_path")
        pagedata = [{k: v for k, v in zip(rownames, val)}]
        return web.json_response(pagedata, status=200)

    async def getEXPageImage(self, request):
        data = await request.json()
        if not validate_required_fields(
            data, ["user", "token", "test", "question", "order"]
        ):
            return web.Response(status=400)
        if not self.server.validate(data["user"], data["token"]):
            return web.Response(status=401)
        if not data["user"] == "manager":
            raise web.HTTPForbidden(reason="I want to speak to the manager")

        ok, val = self.server.getEXPageImage(
            data["test"], data["question"], data["order"]
        )
        if not ok:
            raise web.HTTPBadRequest(reason=val)  # TODO: was 404
        rownames = ("pagename", "md5", "orientation", "id", "server_path")
        pagedata = [{k: v for k, v in zip(rownames, val)}]
        return web.json_response(pagedata, status=200)

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

    # DELETE: /plom/admin/unknownImage
    @authenticate_by_token_required_fields(["fileName", "reason"])
    @write_admin
    def removeUnknownImage(self, data, request):
        """The unknown page is to be discarded.

        Args:
            request (aiohttp.web_request.Request): This has the usual "user"
                and "token" fields but also:

                - fileName (str): identifies the UnknownPage.
                - reason (str): a short reason why which could be canned or
                  free-form from the user.  If the empty string, then a default
                  message may be substituted.

        Returns:
            web.Response: 200 if all went well.
            400 for incorrect fields,
            401 for authentication, or 403 is not manager.
            404 if there isn't any such image, or it is not a UnknownImage,
            with details given in the reason.
        """
        ok, msg = self.server.removeUnknownImage(data["fileName"], data["reason"])
        if not ok:
            raise web.HTTPNotFound(reason=msg)
        return web.Response(status=200)

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

    @authenticate_by_token_required_fields(["fileName", "test", "page", "rotation"])
    @write_admin
    def unknownToTestPage(self, data, request):
        """The unknown page is moved to the indicated tpage.

        The minimal set of groups are reset when this happens
        - namely the group containing the new tpage.

        Args:
            request (aiohttp.web_request.Request): This has the usual "user"
                and "token" fields but also:

                - fileName (str): identifies the UnknownPage.
                - test (str): paper number to map onto (int passed as str).
                - page (str): page number (again, an int)
                - rotation (str): an integer, presumably a multiple of 90
                  0, 90, -90, 180, 270, etc.

        Returns:
            web.Response: 200 if all went well, with a string in JSON which
            can be "collision" if a collision was created or "testPage" in
            the usual successful case.
            400 for incorrect fields,
            401 for authentication, or 403 is not manager. 409 in one of
            various "not found" situations, such as test number or page
            number do not exist.
        """
        status, code, msg = self.server.unknownToTestPage(
            data["fileName"], data["test"], data["page"], data["rotation"]
        )
        if status:
            assert msg is None
            return web.json_response(code, status=200)  # all fine
        if code == "notfound":
            log.warning(msg)
            raise web.HTTPConflict(reason=msg)
        log.warning("Unexpected situation: %s", msg)
        raise web.HTTPBadRequest(reason=f"Unexpected situation: {msg}")

    @authenticate_by_token_required_fields(
        ["fileName", "test", "questions", "rotation"]
    )
    @write_admin
    def unknownToHWPage(self, data, request):
        """Map an unknown page onto one or more HomeworkPages.

        Args:
            request (aiohttp.web_request.Request): This has the usual "user"
                and "token" fields but also:

                - fileName (str): identifies the UnknownPage.
                - test (str): paper number to map onto (int passed as str).
                - questions (list): question numbers, ints.
                - rotation (str): an integer, presumably a multiple of 90
                  0, 90, -90, 180, 270, etc.

        Returns:
            web.Response: 200 if all went well.  400 for incorrect fields,
            401 for authentication, or 403 is not manager. 409 if paper
            number or question number do not exist (e.g., out of range).
        """
        status, code, msg = self.server.unknownToHWPage(
            data["fileName"], data["test"], data["questions"], data["rotation"]
        )
        if status:
            return web.Response(status=200)  # all fine
        if code == "notfound":
            log.warning(msg)
            raise web.HTTPConflict(reason=msg)
        log.warning("Unexpected situation: %s", msg)
        raise web.HTTPBadRequest(reason=f"Unexpected situation: {msg}")

    @authenticate_by_token_required_fields(
        ["fileName", "test", "questions", "rotation"]
    )
    @write_admin
    def unknownToExtraPage(self, data, request):
        """Map an unknown page onto one or more extra pages.

        Args:
            request (aiohttp.web_request.Request): This has the usual "user"
                and "token" fields but also:

                - fileName (str): identifies the UnknownPage.
                - test (str): paper number to map onto (int passed as str).
                - questions (list): question numbers, a list of integers.
                - rotation (str): an integer, presumably a multiple of 90
                  0, 90, -90, 180, 270, etc.

        Returns:
            web.Response: 200 if all went well.  400 for incorrect fields,
            401 for authentication, or 403 is not manager. 409 if paper
            number or question number do not exist (e.g., out of range).
            Also, 409 if one or more questions not scanned (so cannot
            attach extra page).  This is important as otherwise we can
            bypass the scanned mechanism and a test of only extra pages
            could be overlooked (not graded nor returned).
        """
        status, code, msg = self.server.unknownToExtraPage(
            data["fileName"], data["test"], data["questions"], data["rotation"]
        )
        if status:
            return web.Response(status=200)
        if code == "notfound":
            log.warning(msg)
            raise web.HTTPConflict(reason=msg)
        if code == "unscanned":
            log.warning(msg)
            raise web.HTTPConflict(reason=msg)
        log.warning("Unexpected situation: %s", msg)
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
        if code == "notfound":
            log.warning(msg)
            raise web.HTTPConflict(reason=msg)
        log.warning("Unexpected situation: %s", msg)
        raise web.HTTPBadRequest(reason=f"Unexpected situation: {msg}")

    @authenticate_by_token_required_fields(["fileName"])
    @write_admin
    def discardToUnknown(self, data, request):
        ok, msg = self.server.discardToUnknown(data["fileName"])
        if not ok:
            return web.HTTPNotAcceptable(reason=msg)
        return web.Response(status=200)

    @authenticate_by_token_required_fields(["user", "version_map"])
    @write_admin
    def initialiseExamDatabase(self, data, request):
        """Instruct the server to generate paper data in the database."""
        spec = self.server.testSpec
        if not spec:
            raise web.HTTPBadRequest(reason="Server has no spec; cannot initialise DB")

        # this is not strictly-speaking true from an API point of view, Issue #2270.
        if spec["numberToProduce"] < 0:
            raise web.HTTPBadRequest(
                reason=f'Server spec has numberToProduce = {spec["numberToProduce"]};'
                + " in this case you cannot initialise DB without a classlist"
            )

        if len(data["version_map"]) == 0:
            vmap = None
        else:
            vmap = undo_json_packing_of_version_map(data["version_map"])

        try:
            new_vmap = self.server.initialiseExamDatabase(spec, vmap)
        except ValueError as e:
            raise web.HTTPConflict(reason=e) from None

        return web.json_response(new_vmap, status=200)

    @authenticate_by_token_required_fields(["user", "test_number", "vmap_for_test"])
    @write_admin
    def appendTestToExamDatabase(self, data, request):
        """Append given test to database using given version map.

        Returns:
            web.Response: 200 on success and a status message summarizing
            the newly created row.  Errors:

            - 400 for server does not have spec.
            - 401 for authentication, or 403 if not manager.
            - 406 (unacceptable) for problems with version map or spec.
            - 409 (conflict) for row already exists or otherwise cannot
              be created.
            - 500 for unexpected errors.
        """
        spec = self.server.testSpec
        if not spec:
            raise web.HTTPBadRequest(reason="Server has no spec; cannot populate DB")

        # explicitly cast incoming vmap to ints
        try:
            vmap = {int(q): int(v) for q, v in data["vmap_for_test"].items()}
        except (TypeError, ValueError) as e:
            raise web.HTTPNotAcceptable(
                reason=f"Could not convert version map to int: {str(e)}"
            ) from None

        try:
            summary = self.server.appendTestToExamDatabase(
                spec, data["test_number"], vmap
            )
        except ValueError as e:
            raise web.HTTPConflict(reason=str(e)) from None
        except KeyError as e:
            raise web.HTTPNotAcceptable(reason=str(e)) from None
        except RuntimeError as e:
            # uneasy about explicit 500, but these are unexpected
            raise web.HTTPInternalServerError(reason=str(e)) from None
        return web.Response(text=summary, status=200)

    @authenticate_by_token_required_fields([])
    def getGlobalPageVersionMap(self, data, request):
        """Get the mapping between page number and version for all tests.

        Returns:
            dict: dict of dicts, keyed first by paper index then by page
            number.  Both keys are strings b/c of json limitations;
            you may need to iterate and convert back to int.  Fails
            with 409 if the version map database has not been built yet.

        .. caution:: careful not to confuse this with `/plom/admin/questionVersionMap`
            which is much more likely what you are looking for.
        """
        spec = self.server.testSpec
        if not spec:
            raise web.HTTPNotFound(reason="Server has no spec so no version map")
        vers = {}
        for paper_idx in range(1, spec["numberToProduce"] + 1):
            ver = self.server.getPageVersions(paper_idx)
            if not ver:
                _msg = "There is no version map: have you built the database?"
                log.warning(_msg)
                raise web.HTTPConflict(reason=_msg)
            vers[paper_idx] = ver
        return web.json_response(vers, status=200)

    @authenticate_by_token_required_fields([])
    def getQuestionVersionMap(self, data, request):
        """Get the mapping between questions and version for one test.

        Returns:
            dict: keyed by question number.  Note keys will be strings b/c
            of json limitations; you may need to convert back to int.
            Fails with 409 if there is no such paper.
        """
        paper_idx = request.match_info["papernum"]
        vers = self.server.get_question_versions(paper_idx)
        if not vers:
            _msg = f"paper {paper_idx} does not (yet?) have a version map"
            log.warning(_msg)
            raise web.HTTPConflict(reason=_msg)
        return web.json_response(vers, status=200)

    @authenticate_by_token_required_fields([])
    def getGlobalQuestionVersionMap(self, data, request):
        """Get the mapping between question and version for all tests.

        Returns:
            dict: dict of dicts, keyed first by paper index then by
            question number.  Both keys will become strings b/c of
            json limitations; you may need to convert back to int.
            If the server does not yet have any database, the version
            map will be empty.
        """
        vermap = self.server.get_all_question_versions()
        return web.json_response(vermap, status=200)

    # Some more bundle things

    @authenticate_by_token_required_fields(["user", "filename"])
    @readonly_admin
    def getBundleFromImage(self, data, request):
        """Returns the name of the bundle that contains the given image.

        If DB can't find the file then returns HTTPGone error.
        If not manager, then raise an HTTPUnauthorized error.
        """
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
        router.add_get("/plom/admin/bundle", self.doesBundleExist)
        router.add_put("/plom/admin/bundle", self.createNewBundle)
        router.add_get("/plom/admin/bundle/list", self.listBundles)
        router.add_get("/plom/admin/sidToTest", self.sidToTest)
        router.add_put("/plom/admin/testPages/{tpv}", self.uploadTestPage)
        router.add_put("/plom/admin/hwPages", self.uploadHWPage)
        router.add_put("/plom/admin/unknownPages", self.uploadUnknownPage)
        router.add_put("/plom/admin/collidingPages/{tpv}", self.uploadCollidingPage)
        router.add_put("/plom/admin/missingTestPage", self.replaceMissingTestPage)
        router.add_put("/plom/admin/missingDNMPage", self.replaceMissingDNMPage)
        router.add_put("/plom/admin/missingIDPage", self.replaceMissingIDPage)
        router.add_put("/plom/admin/missingHWQuestion", self.replaceMissingHWQuestion)
        router.add_delete("/plom/admin/scannedPages", self.removeAllScannedPages)
        router.add_delete("/plom/admin/singlePage", self.removeSinglePage)
        router.add_get("/plom/admin/scannedTPage", self.getTPageImage)
        router.add_get("/plom/admin/scannedHWPage", self.getHWPageImage)
        router.add_get("/plom/admin/scannedEXPage", self.getEXPageImage)
        router.add_get("/plom/admin/unknownPages", self.getUnknownPages)
        router.add_get("/plom/admin/discardedPages", self.getDiscardedPages)
        router.add_get("/plom/admin/collidingPageNames", self.getCollidingPageNames)
        router.add_get("/plom/admin/collidingImage", self.getCollidingImage)
        router.add_get("/plom/admin/checkTPage", self.checkTPage)
        router.add_delete("/plom/admin/unknownImage", self.removeUnknownImage)
        router.add_delete("/plom/admin/collidingImage", self.removeCollidingImage)
        router.add_put("/plom/admin/unknownToTestPage", self.unknownToTestPage)
        router.add_put("/plom/admin/unknownToHWPage", self.unknownToHWPage)
        router.add_put("/plom/admin/unknownToExtraPage", self.unknownToExtraPage)
        router.add_put("/plom/admin/collidingToTestPage", self.collidingToTestPage)
        router.add_put("/plom/admin/discardToUnknown", self.discardToUnknown)
        router.add_put("/plom/admin/initialiseDB", self.initialiseExamDatabase)
        router.add_put("/plom/admin/appendTestToDB", self.appendTestToExamDatabase)
        router.add_get("/plom/admin/pageVersionMap", self.getGlobalPageVersionMap)
        router.add_get(
            "/plom/admin/questionVersionMap/{papernum}", self.getQuestionVersionMap
        )
        router.add_get(
            "/plom/admin/questionVersionMap", self.getGlobalQuestionVersionMap
        )
        router.add_get("/plom/admin/bundleFromImage", self.getBundleFromImage)
        router.add_get("/plom/admin/imagesInBundle", self.getImagesInBundle)
        router.add_get("/plom/admin/bundlePage", self.getPageFromBundle)
