# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2019-2021 Andrew Rechnitzer
# Copyright (C) 2020-2021 Colin B. Macdonald
# Copyright (C) 2020 Vala Vakilian

from aiohttp import web

from .routeutils import authenticate_by_token, authenticate_by_token_required_fields
from .routeutils import validate_required_fields, log_request
from .routeutils import log


class SolutionHandler:
    def __init__(self, plomServer):
        self.server = plomServer

    @authenticate_by_token_required_fields(["user"])
    def getSolutionStatus(self, data, request):
        status = self.server.getSolutionStatus()

    @authenticate_by_token_required_fields(["user", "question", "version"])
    def getSolutionImage(self, data, request):
        q = data["question"]
        v = data["version"]
        solutionFile = self.server.getSolutionImage(question, version)
        if solutionFile is not None:
            return web.FileResponse(solutionFile, status=200)
        else:
            return web.response(status=404)

        pass

    def uploadSolutionImage(self, data, request):
        pass

    def setUpRoutes(self, router):
        """Adds the response functions to the router object.

        Args:
            router (aiohttp.web_urldispatcher.UrlDispatcher): Router object which we will add the response functions to.
        """
        router.add_put("/admin/solution", self.uploadSolutionImage)
        router.add_get("/admin/solution", self.getSolutionImage)
        router.add_get("/REP/solutions", self.getSolutionStatus)
