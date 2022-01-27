# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2019-2020 Andrew Rechnitzer
# Copyright (C) 2020-2022 Colin B. Macdonald
# Copyright (C) 2020 Vala Vakilian

from aiohttp import web

from .routeutils import (
    authenticate_by_token,
    authenticate_by_token_required_fields,
    no_authentication_only_log_request,
)
from .routeutils import validate_required_fields, log_request
from .routeutils import log

from plom import SpecVerifier


class UserInitHandler:
    def __init__(self, plomServer):
        self.server = plomServer

    # @routes.get("/Version")
    @no_authentication_only_log_request
    async def version(self, request):
        return web.Response(
            text="Plom server version {} with API {}".format(
                self.server.Version, self.server.API
            ),
            status=200,
        )

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
    def createModifyUser(self, data, request):
        # update password of existing user, or create new user.
        theuser = request.match_info["user"]
        rval = self.server.createModifyUser(theuser, data["password"])
        if rval[0]:  # successful
            if rval[1]:  # created new user
                log.info('Manager created new user "{}"'.format(theuser))
                return web.Response(status=201)
            else:  # updated password of existing user
                log.info('Manager updated password of user "{}"'.format(theuser))
                return web.Response(status=202)
        else:  # failed.
            log.info('Manager failed to create/modify user "{}"'.format(theuser))
            return web.Response(text=rval[1], status=406)

    # @routes.put("/enable/{user}")
    async def enableUser(self, request):
        log_request("enableUser", request)
        data = await request.json()
        if not data["user"] == "manager":
            raise web.HTTPForbidden(reason="I want to speak to the manager")
        theuser = request.match_info["user"]
        if theuser in ("manager", "HAL"):
            raise web.HTTPBadRequest(reason="HAL/manager cannot be enabled/disabled")
        log.info('Enabling user "%s"', theuser)
        self.server.setUserEnable(theuser, True)
        return web.Response(status=200)

    # @routes.put("/disable/{user}")
    async def disableUser(self, request):
        log_request("disableUser", request)
        data = await request.json()
        if not data["user"] == "manager":
            raise web.HTTPForbidden(reason="I want to speak to the manager")
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

    # @routes.put("/admin/reloadUsers")
    async def adminReloadUsers(self, request):
        log_request("adminReloadUsers", request)
        # TODO: future proof: require user here and check for manager
        # TODO: safer to do this with token auth, to centralize pw auth?
        data = await request.json()
        # TODO: future proof by requiring username here too?
        if not validate_required_fields(data, ["pw"]):
            return web.Response(status=400)  # malformed request.

        rmsg = self.server.reloadUsers(data["pw"])
        # returns either True (success) or False (auth-error)
        if rmsg:
            return web.json_response(status=200)  # all good
        else:
            return web.Response(status=401)  # you are not authorised

    # @routes.get("/info/spec")
    @no_authentication_only_log_request
    async def info_spec(self, request):
        """Return the public part of the server specification.

        Response:
            200: the public part of the spec.
            400: spec not found (server does not have one yet).
        """
        spec = self.server.info_spec()
        if not spec:
            raise web.HTTPBadRequest(reason="Server does not yet have a spec")
        return web.json_response(spec, status=200)

    # @routes.put("/info/spec")
    @authenticate_by_token_required_fields(["user", "spec"])
    def put_spec(self, data, request):
        """Accept an uploaded exam specification.

        Response:
            403: only manager can upload a spec.
            400: the provided spec is not valid.
            409: Conflict: server has already populated the database.
            200: new spec file accepted.  TODO: would be polite to inform
                caller if we already had one or not.
        """
        if not data["user"] == "manager":
            raise web.HTTPForbidden(reason="Not manager")

        if self.server.DB.is_paper_database_populated():
            raise web.HTTPConflict(reason="Server has populated DB: cannot accept spec")
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

        Response:
            200: the short name.
            400: server has no spec.
        """
        name = self.server.InfoShortName()
        if not name:
            raise web.HTTPBadRequest(reason="Server does not yet have a spec")
        return web.Response(text=name, status=200)

    def setUpRoutes(self, router):
        router.add_get("/Version", self.version)
        router.add_delete("/users/{user}", self.closeUser)
        router.add_put("/users/{user}", self.giveUserToken)
        router.add_put("/admin/reloadUsers", self.adminReloadUsers)
        router.add_get("/info/shortName", self.InfoShortName)
        router.add_get("/info/spec", self.info_spec)
        router.add_put("/info/spec", self.put_spec)
        router.add_delete("/authorisation", self.clearAuthorisation)
        router.add_delete("/authorisation/{user}", self.clearAuthorisationUser)
        router.add_post("/authorisation/{user}", self.createModifyUser)
        router.add_put("/enable/{user}", self.enableUser)
        router.add_put("/disable/{user}", self.disableUser)
