# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2019-2021 Andrew Rechnitzer
# Copyright (C) 2020-2023 Colin B. Macdonald
# Copyright (C) 2020 Vala Vakilian

from aiohttp import web, MultipartReader

from .routeutils import authenticate_by_token_required_fields
from .routeutils import validate_required_fields


class SolutionHandler:
    """The Solution Handler interfaces between the HTTP API and the server itself.

    These routes handle requests related to solutions.
    """

    def __init__(self, plomServer):
        self.server = plomServer

    @authenticate_by_token_required_fields(["user"])
    def getSolutionStatus(self, data, request):
        soln_dict = self.server.getSolutionStatus()
        return web.json_response(soln_dict, status=200)

    @authenticate_by_token_required_fields(["user", "question", "version"])
    def getSolutionImage(self, data, request):
        q = data["question"]
        v = data["version"]
        solutionFile = self.server.getSolutionImage(q, v)
        if not solutionFile:
            raise web.HTTPNotFound(reason=f"No solution for question {q} version {v}")
        return web.FileResponse(solutionFile, status=200)

    @authenticate_by_token_required_fields(["user", "question", "version"])
    def deleteSolutionImage(self, data, request):
        q = data["question"]
        v = data["version"]
        if self.server.deleteSolutionImage(q, v):
            return web.Response(status=200)
        else:
            return web.Response(status=204)

    async def uploadSolutionImage(self, request):
        reader = MultipartReader.from_response(request)
        # Dealing with the metadata.
        soln_metadata_object = await reader.next()

        if soln_metadata_object is None:  # weird error
            return web.Response(status=406)  # should have sent 2 parts
        soln_metadata = await soln_metadata_object.json()
        # Validate that the dictionary has these fields.
        if not validate_required_fields(
            soln_metadata, ["user", "token", "question", "version", "md5sum"]
        ):
            return web.Response(status=400)
        # make sure user = manager
        if soln_metadata["user"] != "manager":
            return web.Response(status=401)
        # Validate username and token.
        if not self.server.validate(soln_metadata["user"], soln_metadata["token"]):
            return web.Response(status=401)
        # Get the image.
        soln_image_object = await reader.next()
        if soln_image_object is None:  # weird error
            return web.Response(status=406)  # should have sent 2 parts
        soln_image = await soln_image_object.read()
        if self.server.uploadSolutionImage(
            soln_metadata["question"],
            soln_metadata["version"],
            soln_metadata["md5sum"],
            soln_image,
        ):
            return web.Response(status=200)  # all okay
        else:
            return web.Response(status=406)  # some file problem

    def setUpRoutes(self, router):
        """Adds the response functions to the router object.

        Args:
            router (aiohttp.web_urldispatcher.UrlDispatcher): Router object which we will add the response functions to.
        """
        router.add_put("/plom/admin/solution", self.uploadSolutionImage)
        router.add_delete("/plom/admin/solution", self.deleteSolutionImage)
        router.add_get("/MK/solution", self.getSolutionImage)
        router.add_get("/REP/solutions", self.getSolutionStatus)
