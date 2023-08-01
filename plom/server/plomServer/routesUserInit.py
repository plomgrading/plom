# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2019-2020 Andrew Rechnitzer
# Copyright (C) 2020-2023 Colin B. Macdonald
# Copyright (C) 2020 Vala Vakilian
# Copyright (C) 2022 Edith Coates

from aiohttp import web

from .routeutils import authenticate_by_token_required_fields
from .routeutils import no_authentication_only_log_request
from .routeutils import validate_required_fields, log_request
from .routeutils import write_admin
from .routeutils import log

from plom import SpecVerifier


class UserInitHandler:
    """The UserInit Handler interfaces between the HTTP API and the server itself.

    These routes handle requests related to administration of user accounts.
    """

    def __init__(self, plomServer):
        self.server = plomServer

    def _version_string(self):
        return f"Legacy Plom server version {self.server.Version} with API {self.server.API}"

    # @routes.get("/Version")
    @no_authentication_only_log_request
    async def version(self, request):
        return web.Response(
            text=self._version_string(),
            status=200,
        )

    # @routes.get("/info/server")
    @no_authentication_only_log_request
    async def get_server_info(self, request):
        info = {
            "product_string": "Legacy Plom Server",
            "version": self.server.Version,
            "API_version": self.server.API,
            "version_string": self._version_string(),
            # TODO: "acceptable_client_API": [100, 101, 107],
        }
        return web.json_response(info, status=200)

    # @routes.delete("/authorisation")
    async def clearAuthorisation(self, request):
        log_request("clearAuthorisation", request)
        data = await request.json()
        if not validate_required_fields(data, ["user", "password"]):
            return web.Response(status=400)  # malformed request.
        if not self.server.checkPassword(data["user"], data["password"]):
            return web.Response(status=401)
        log.info('User "{}" force-logout self'.format(data["user"]))
        self.server.closeUser(data["user"])
        return web.Response(status=200)

    # @routes.delete("/users/{user}")
    @authenticate_by_token_required_fields(["user"])
    def closeUser(self, data, request):
        """User self-indicates they are logging out, revoke token and tasks.

        Returns:
            aiohttp.web.Response: 200 for success, unless a user tries to
            close another which is BadRequest (400) or user is already
            logged out, or nonexistent, both of which will give an
            Unauthorized (401).
        """
        # TODO: should manager be allowed to do this for anyone?
        if data["user"] != request.match_info["user"]:
            raise web.HTTPBadRequest(reason="You cannot close other users")
        self.server.closeUser(data["user"])
        return web.Response(status=200)

    # @routes.delete("/authorisation/{user}")
    @authenticate_by_token_required_fields(["user"])
    def clearAuthorisationUser(self, data, request):
        # Only manager can clear other users, via token auth
        # TODO: ok for manager to clear manager via token auth?
        # TODO: should other users be able to use this on themselves?
        if not data["user"] == "manager":
            return web.Response(status=400)  # malformed request.
        theuser = request.match_info["user"]
        self.server.closeUser(theuser)
        log.info('Manager force-logout user "{}"'.format(theuser))
        return web.Response(status=200)

    # @routes.post("/authorisation/{user}")
    @authenticate_by_token_required_fields(["password"])
    @write_admin
    def createUser(self, data, request):
        """Create a new user."""
        theuser = request.match_info["user"]
        ok, val = self.server.createUser(theuser, data["password"])
        if not ok:
            log.info('Manager failed to create user "%s"', theuser)
            return web.HTTPNotAcceptable(reason=val)
        else:
            log.info('Manager created new user "%s"', theuser)
            return web.Response(status=200)

    # @routes.patch("/authorisation/{user}")
    @authenticate_by_token_required_fields(["password"])
    @write_admin
    def changeUserPassword(self, data, request):
        """Change an existing user's password."""
        theuser = request.match_info["user"]
        ok, val = self.server.changeUserPassword(theuser, data["password"])
        if not ok:
            log.info('Manager failed to change the password of user "%s"', theuser)
            return web.HTTPNotAcceptable(reason=val)
        else:
            log.info('Manager changed password of user "%s"', theuser)
            return web.Response(status=200)

    # @routes.put("/enable/{user}")
    @authenticate_by_token_required_fields([])
    @write_admin
    def enableUser(self, data, request):
        theuser = request.match_info["user"]
        if theuser in ("manager", "HAL"):
            raise web.HTTPBadRequest(reason="HAL/manager cannot be enabled/disabled")
        log.info('Enabling user "%s"', theuser)
        self.server.setUserEnable(theuser, True)
        return web.Response(status=200)

    # @routes.put("/disable/{user}")
    @authenticate_by_token_required_fields([])
    @write_admin
    def disableUser(self, data, request):
        theuser = request.match_info["user"]
        if theuser == "manager":
            raise web.HTTPBadRequest(reason="Cannot disable the manager account")
        if theuser == "HAL":
            raise web.HTTPBadRequest(
                reason="Just what do you think you're doing, Dave?"
            )
        log.info('Disabling user "%s"', theuser)
        self.server.setUserEnable(theuser, False)
        return web.Response(status=200)

    # @routes.put("/users/{user}")
    async def giveUserToken(self, request):
        log_request("giveUserToken", request)
        ip = request.remote
        data = await request.json()
        if not validate_required_fields(data, ["user", "pw", "api", "client_ver"]):
            return web.Response(status=400)  # malformed request.
        if data["user"] != request.match_info["user"]:
            return web.Response(status=400)  # malformed request.

        rmsg = self.server.giveUserToken(
            data["user"], data["pw"], data["api"], data["client_ver"], ip
        )
        if rmsg[0]:
            return web.json_response(rmsg[1], status=200)  # all good, return the token
        elif rmsg[1].startswith("API"):
            return web.json_response(rmsg[2], status=400)
        elif rmsg[1].startswith("HasToken"):
            return web.json_response(rmsg[2], status=409)
        else:
            # various sorts of non-auth conflated: response has details
            return web.json_response(rmsg[2], status=401)

    # @routes.get("/info/exam")
    @authenticate_by_token_required_fields([])
    def get_exam_info(self, data, request):
        spec = self.server.info_spec()
        if not spec:
            raise web.HTTPBadRequest(reason="Server does not yet have a spec")
        info = {
            "current_largest_paper_num": spec["numberToProduce"],
        }
        return web.json_response(info, status=200)

    # @routes.get("/info/spec")
    @no_authentication_only_log_request
    async def info_spec(self, request):
        """Return the public part of the server specification.

        Returns:
            aiohttp.json_response:

            - 200: the public part of the spec.
            - 400: spec not found (server does not have one yet).
        """
        spec = self.server.info_spec()
        if not spec:
            raise web.HTTPBadRequest(reason="Server does not yet have a spec")
        return web.json_response(spec, status=200)

    # @routes.put("/info/spec")
    @authenticate_by_token_required_fields(["user", "spec"])
    @write_admin
    def put_spec(self, data, request):
        """Accept an uploaded exam specification.

        Returns:
            aiohttp.Response:

            - 403: only manager can upload a spec.
            - 400: the provided spec is not valid.
            - 409: Conflict: server has already initialised or populated
              the database.
            - 200: new spec file accepted.  TODO: would be polite to inform
              caller if we already had one or not.
        """
        if self.server.DB.is_paper_database_initialised():
            raise web.HTTPConflict(
                reason="Server has initialised DB: cannot accept spec"
            )
        sv = SpecVerifier(data["spec"])
        try:
            sv.verifySpec(verbose="log")
            sv.checkCodes(verbose="log")
        except ValueError as e:
            raise web.HTTPBadRequest(reason=f"{e}")
        sv.saveVerifiedSpec()
        self.server.testSpec = SpecVerifier.load_verified()
        log.info("spec loaded: %s", self.server.info_spec())
        return web.Response()

    # @routes.get("/info/shortName")
    @no_authentication_only_log_request
    async def InfoShortName(self, request):
        """The short name of the exam.

        DEPRECATED 0.14.0: no modern callers, only for old clients.

        Returns:
            aiohttp.Response: 200 and the short name or 400 if the
            server has no spec.
        """
        name = self.server.InfoShortName()
        if not name:
            raise web.HTTPBadRequest(reason="Server does not yet have a spec")
        return web.Response(text=name, status=200)

    def setUpRoutes(self, router):
        router.add_get("/Version", self.version)
        router.add_get("/info/server", self.get_server_info)
        router.add_get("/info/exam", self.get_exam_info)
        router.add_delete("/users/{user}", self.closeUser)
        router.add_put("/users/{user}", self.giveUserToken)
        router.add_get("/info/shortName", self.InfoShortName)
        router.add_get("/info/spec", self.info_spec)
        router.add_put("/info/spec", self.put_spec)
        router.add_delete("/authorisation", self.clearAuthorisation)
        router.add_delete("/authorisation/{user}", self.clearAuthorisationUser)
        router.add_post("/authorisation/{user}", self.createUser)
        router.add_patch("/authorisation/{user}", self.changeUserPassword)
        router.add_put("/enable/{user}", self.enableUser)
        router.add_put("/disable/{user}", self.disableUser)
