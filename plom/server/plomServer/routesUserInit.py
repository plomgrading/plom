# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2019-2020 Andrew Rechnitzer
# Copyright (C) 2020-2021 Colin B. Macdonald
# Copyright (C) 2020 Vala Vakilian

import os
import json

from aiohttp import web, MultipartWriter, MultipartReader

from .routeutils import (
    authenticate_by_token,
    authenticate_by_token_required_fields,
    no_authentication_only_log_request,
)
from .routeutils import validate_required_fields, log_request
from .routeutils import log


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
        # TODO: should manager be allowed to do this for anyone?
        if data["user"] != request.match_info["user"]:
            return web.Response(status=400)  # malformed request.
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
        if rval[0]:  # successfull
            if rval[1]:  # created new user
                log.info('Manager created new user "{}"'.format(theuser))
                return web.Response(status=201)
            else:  # updated password of existing user
                log.info('Manager updated password of user "{}"'.format(theuser))
                return web.Response(status=202)
        else:  # failed.
            log.info('Manager failed to create/modify user "{}"'.format(theuser))
            return web.Response(text=rval[1], status=406)

    # @routes.put("/enableDisable/{user}")
    async def setUserEnable(self, request):
        log_request("setUserEnable", request)
        data = await request.json()
        if not data["user"] == "manager":
            return web.Response(status=400)  # malformed request.
        theuser = request.match_info["user"]
        if theuser in [
            "manager",
            "HAL",
        ]:  # cannot switch manager off... Just what do you think you're doing, Dave?
            return web.Response(status=400)  # malformed request.
        log.info(
            'Set enable/disable for User "{}" = {}'.format(theuser, data["enableFlag"])
        )
        self.server.setUserEnable(theuser, data["enableFlag"])
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
            return web.json_response(
                rmsg[1], status=400
            )  # api error - return the error message
        elif rmsg[1].startswith("UHT"):
            return web.json_response(rmsg[1], status=409)  # user has token already.
        else:
            return web.json_response(rmsg[1], status=401)  # you are not authorised

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
        spec = self.server.info_spec()
        if not spec:
            return web.Response(status=404)
        return web.json_response(spec, status=200)

    # @routes.get("/info/shortName")
    @no_authentication_only_log_request
    async def InfoShortName(self, request):
        rmsg = self.server.InfoShortName()
        if rmsg[0]:
            return web.Response(text=rmsg[1], status=200)
        else:  # this should not happen
            return web.Response(status=404)

    def setUpRoutes(self, router):
        router.add_get("/Version", self.version)
        router.add_delete("/users/{user}", self.closeUser)
        router.add_put("/users/{user}", self.giveUserToken)
        router.add_put("/admin/reloadUsers", self.adminReloadUsers)
        router.add_get("/info/shortName", self.InfoShortName)
        router.add_get("/info/spec", self.info_spec)
        router.add_delete("/authorisation", self.clearAuthorisation)
        router.add_delete("/authorisation/{user}", self.clearAuthorisationUser)
        router.add_post("/authorisation/{user}", self.createModifyUser)
        router.add_put("/enableDisable/{user}", self.setUserEnable)
