# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2019-2021 Andrew Rechnitzer
# Copyright (C) 2020-2023 Colin B. Macdonald
# Copyright (C) 2020 Vala Vakilian

from aiohttp import web

from .routeutils import authenticate_by_token, authenticate_by_token_required_fields
from .routeutils import validate_required_fields, log_request
from .routeutils import log


class RubricHandler:
    """The Rubric Handler interfaces between the HTTP API and the server itself.

    These routes handle requests related to rubrics.
    """

    def __init__(self, plomServer):
        self.server = plomServer

    def validateRubric(self, username, rubric):
        """Do some simple validation of the rubric

        Args:
            username (str): the name of the user trying to create the rubric
            rubric (dict): a dict containing the rubric info
        Returns:
            bool: true if valid, false otherwise.
        """
        # check rubric has minimal fields needed
        need_fields = ("kind", "value", "display_delta", "text", "question")
        if any(x not in rubric for x in need_fields):
            return False
        # check question number is in range
        if (
            rubric["question"] <= 0
            or rubric["question"] > self.server.testSpec["numberOfQuestions"]
        ):
            return False
        # set maxMark for checking marks are in range.
        maxMark = self.server.testSpec["question"][str(rubric["question"])]["mark"]

        if rubric["kind"] == "neutral":
            # neutral rubric must have no delta - ie delta == '.'
            if rubric["display_delta"] != ".":
                return False
            # must have some text
            if len(rubric["text"].strip()) == 0:
                return False
            # do we care if its int/None?
            # if not (rubric["value"] is None or isinstance(rubric["value"], int)):
            #     return False
            # TODO: should we enforce value=0/None?
            if not (rubric["value"] is None or int(rubric["value"]) == 0):
                return False

        elif rubric["kind"] == "relative":
            # must have some text
            if len(rubric["text"].strip()) == 0:
                return False
            # do we care if its int?
            # if not isinstance(rubric["value"], int):
            #     return False
            # the delta must be of the form -k or +k
            if rubric["display_delta"][0] not in ["-", "+"]:
                return False
            # check rest of delta string is numeric
            if not rubric["display_delta"][1:].isnumeric():
                return False
            # check delta is in range
            idelta = int(rubric["display_delta"])
            if (idelta < -maxMark) or (idelta > maxMark) or (idelta == 0):
                return False

        elif rubric["kind"] == "absolute":
            # must have some text
            if len(rubric["text"].strip()) == 0:
                return False
            # do we care if its int?
            # if not isinstance(rubric["value"], int):
            #     return False
            # check score in range
            value = int(rubric["value"])
            if (value < 0) or (value > maxMark):
                return False

        else:  # rubric kind must be neutral, relative, delta or absolute
            return False

        # passes tests
        return True

    # @routes.put("/MK/rubric")
    @authenticate_by_token_required_fields(["user", "rubric"])
    def McreateRubric(self, data, request):
        """Respond with updated comment list and add received comments to the database.

        Args:
            data (dict): A dictionary including user/token and the new rubric to be created
            request (aiohttp.web_request.Request): A request of type PUT /MK/rubric.

        Returns:
            aiohttp.web_response.Response: either 200 with the new key
            or 406 if sent rubric was incomplete.
        """
        username = data["user"]
        new_rubric = data["rubric"]

        if not self.validateRubric(username, new_rubric):
            return web.HTTPNotAcceptable(reason="Rubric info incomplete/inconsistent")

        ok, key_or_reason = self.server.McreateRubric(username, new_rubric)
        if ok:
            return web.json_response(key_or_reason, status=200)
        return web.HTTPNotAcceptable(reason=key_or_reason)

    # @routes.get("/MK/rubric")
    @authenticate_by_token_required_fields(["user"])
    def MgetRubrics(self, data, request):
        """Respond with the current comment list.

        Args:
            data (dict): A dictionary including user/token
            request (aiohttp.web_request.Request): A request of type GET /MK/rubric.

        Returns:
            aiohttp.web_response.Response: List of all comments in DB
        """
        username = data["user"]

        rubrics = self.server.MgetRubrics()
        return web.json_response(rubrics, status=200)

    # @routes.get("/MK/rubric/{question}")
    @authenticate_by_token_required_fields(["user"])
    def MgetRubricsByQuestion(self, data, request):
        """Respond with the comment list for a particular question.

        Args:
            data (dict): A dictionary including user/token
            request (aiohttp.web_request.Request): A request of type GET /MK/rubric/{question}.

        Returns:
            aiohttp.web_response.Response: List of all comments in DB
        """
        username = data["user"]
        question = request.match_info["question"]

        rubrics = self.server.MgetRubrics(question)
        return web.json_response(rubrics, status=200)

    # @routes.patch("/MK/rubric/{key}")
    @authenticate_by_token_required_fields(["user", "rubric"])
    def MmodifyRubric(self, data, request):
        """Add modify rubric to DB and respond with its key

        Args:
            data (dict): A dictionary including user/token and the new rubric to be created
            request (aiohttp.web_request.Request): A request of type GET /MK/rubric.

        Returns:
            aiohttp.web_response.Response: either 200 with the key or
            406 if sent rubric was incomplete or inconsistent,
            409 if no rubric found, or some unexpected situation.
        """
        username = data["user"]
        updated_rubric = data["rubric"]
        key = request.match_info["key"]

        if key != updated_rubric["id"]:
            return web.HTTPBadRequest(reason="Key mismatch in request")

        if not self.validateRubric(username, updated_rubric):
            return web.HTTPNotAcceptable(reason="Sent rubric was inconsistent")

        ok, key_or_reason = self.server.MmodifyRubric(username, key, updated_rubric)
        if ok:
            return web.json_response(key_or_reason, status=200)
        if key_or_reason == "incomplete":
            return web.HTTPNotAcceptable(reason="Sent rubric was incomplete")
        elif key_or_reason == "noSuchRubric":
            return web.HTTPConflict(reason="No rubric with that key found")
        return web.HTTPConflict(reason=f"Unexpected error/bug: '{key_or_reason}'")

    # @routes.get("/MK/user/{user}/{question}")
    @authenticate_by_token_required_fields(["user", "question"])
    def MgetUserRubricPanes(self, data, request):
        """Get user's rubric-panes configuration from server

        Args:
            data (dict): A dictionary including user/token and question number.
            request (aiohttp.web_request.Request): GET `/MK/user/{user}/{question}`.

        Returns:
            aiohttp.web_response.Response: success and the config (as json),
            or 204 if nothing available.  Error responses:

            - HTTPUnauthorized
            - HTTPBadRequest: inconsistent question or missing fields.
            - HTTPForbidden: trying to save to another user.
        """
        username = data["user"]
        question = data["question"]
        save_to_user = request.match_info["user"]
        questionCheck = request.match_info["question"]

        if int(question) != int(questionCheck):
            raise web.HTTPBadRequest(reason="question numbers inconsistent")
        if username != save_to_user:
            # TODO maybe manager should be able to?
            raise web.HTTPForbidden(reason="you can only access your own rubric data")

        rval = self.server.MgetUserRubricPanes(save_to_user, question)
        if rval[0]:  # worked
            return web.json_response(rval[1], status=200)
        else:  # nothing there.
            return web.Response(status=204)

    # @routes.put("/MK/user/{user}/{question}")
    @authenticate_by_token_required_fields(["user", "rubric_config", "question"])
    def MsaveUserRubricPanes(self, data, request):
        """Add new rubric to DB and respond with its key

        Args:
            data (dict): A dictionary including user/token and a blob of data to save
                for the user's rubric tab setup.
            request (aiohttp.web_request.Request): PUT `/MK/user/{user}/{question}`.

        Returns:
            aiohttp.web_response.Response: 200 on success or

            - HTTPUnauthorized
            - HTTPBadRequest: inconsistent question or missing fields.
            - HTTPForbidden: trying to save to another user.
        """
        username = data["user"]
        question = data["question"]
        rubricConfig = data["rubric_config"]
        save_to_user = request.match_info["user"]
        questionCheck = request.match_info["question"]

        if int(question) != int(questionCheck):
            raise web.HTTPBadRequest(reason="question numbers inconsistent")
        if username != save_to_user:
            # TODO maybe manager should be able to?
            raise web.HTTPForbidden(reason="you can only save to your own rubric data")

        self.server.MsaveUserRubricPanes(save_to_user, question, rubricConfig)
        return web.Response(status=200)

    # =====================
    # rubric analysis stuff

    @authenticate_by_token_required_fields(["user"])
    def RgetTestRubricMatrix(self, data, request):
        """Respond with dict encoding test-rubric counts.

        Responds with status 200/401.

        Args:
            data (dict): A dictionary having the user/token.
            request (aiohttp.web_request.Request): Request of type GET /REP/test_rubric_adjacency.

        Returns:
            aiohttp.web_response.Response: A response including metadata
            encoding the test-rubric adjacency / count matrix. The matrix
            is encoded as an adjacency list, i.e.,
            ``{testnumber: [rubric_id1, rubric_id2, ...]}``
            where `(test_n, rubric_k)` means that `rubric_k` was used in
            `test_n`.
        """

        if not data["user"] == "manager":
            return web.Response(status=401)
        rmsg = self.server.RgetTestRubricMatrix()
        # is a dict of the form blah[test_number][rubric_key] =  count

        return web.json_response(rmsg, status=200)

    @authenticate_by_token_required_fields(["user"])
    def RgetRubricCounts(self, data, request):
        """Respond with dict encoding rubric counts and other minimal info.

        Responds with status 200/401.

        Args:
            data (dict): A dictionary having the user/token.
            request (aiohttp.web_request.Request): Request of type GET /REP/rubric/counts.

        Returns:
            aiohttp.web_response.Response: A response including metadata encoding the rubric counts and min info. Returns a list of rubrics, and for each rubric we give a dict listing its id, kind, question, delta, text, user who created it, and the count of how many tests it has been used in.
        """

        if not data["user"] == "manager":
            return web.Response(status=401)
        rmsg = self.server.RgetRubricCounts()

        return web.json_response(rmsg, status=200)

    @authenticate_by_token_required_fields(["user"])
    def RgetRubricDetails(self, data, request):
        """Respond with dict encoding rubric counts and other minimal info.

        Responds with status 200/401/BadRequest.

        Args:
            data (dict): A dictionary having the user/token.
            request (aiohttp.web_request.Request): Request of type GET /REP/rubric/key.

        Returns:
            aiohttp.web_response.Response: A response including metadata encoding the rubric details inc which tests use it. More precisely, we return a dict that gives the rurbrics id, kind, question, delta, text, who created it, tags, meta, count, creation and modification times, and a list of test numbers in which it was used.
        """

        if not data["user"] == "manager":
            return web.Response(status=401)
        key = request.match_info["key"]
        rmsg = self.server.RgetRubricDetails(key)
        if rmsg[0]:
            return web.json_response(rmsg[1], status=200)
        else:
            raise web.HTTPBadRequest(reason="no such rubric")

    def setUpRoutes(self, router):
        """Adds the response functions to the router object.

        Args:
            router (aiohttp.web_urldispatcher.UrlDispatcher): Router object which we will add the response functions to.
        """
        router.add_put("/MK/rubric", self.McreateRubric)
        router.add_get("/MK/rubric", self.MgetRubrics)
        router.add_get("/MK/rubric/{question}", self.MgetRubricsByQuestion)
        router.add_patch("/MK/rubric/{key}", self.MmodifyRubric)
        router.add_get("/MK/user/{user}/{question}", self.MgetUserRubricPanes)
        router.add_put("/MK/user/{user}/{question}", self.MsaveUserRubricPanes)
        router.add_get("/REP/test_rubric_matrix", self.RgetTestRubricMatrix)
        router.add_get("/REP/rubric/counts", self.RgetRubricCounts)
        router.add_get("/REP/rubric/{key}", self.RgetRubricDetails)


##
