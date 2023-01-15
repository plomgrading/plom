# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2019-2022 Andrew Rechnitzer
# Copyright (C) 2020-2022 Colin B. Macdonald
# Copyright (C) 2020 Vala Vakilian
# Copyright (C) 2021 Nicholas J H Lai

from aiohttp import web

from .routeutils import authenticate_by_token_required_fields
from .routeutils import readonly_admin


class ReportHandler:
    """The Report Handler interfaces between the HTTP API and the server itself.

    These routes handle requests related to reporting such as
    information requests about progress and late-stage actions
    such as reassembly.  Typically, these are manager-only calls.
    """

    def __init__(self, plomServer):
        self.server = plomServer

    # @routes.get("/REP/scanned")
    @authenticate_by_token_required_fields(["user"])
    def RgetScannedTests(self, data, request):
        """Respond with a dictionary of completed exams.

        Responds with status 200/401.

        Args:
            data (dict): A dictionary having the user/token.
            request (aiohttp.web_request.Request): Request of type GET /REP/scanned.

        Returns:
            aiohttp.web_response.Response:
        """

        if not data["user"] in ("manager", "scanner"):
            return web.Response(status=401)
        # A dictionary that involves the complete tests : key:exam_number, value: list of lists
        #   involving the page and the page version.
        # Ex: {2: [['t.1', 1], ['t.2', 1], ['t.3', 1], ['t.4', 1], ['t.5', 1], ['t.6', 1]], ... }
        return web.json_response(self.server.RgetScannedTests(), status=200)

    # @routes.get("/REP/incomplete")
    @authenticate_by_token_required_fields(["user"])
    def RgetIncompleteTests(self, data, request):
        """Respond with the incomplete exams, providing information on individual pages.

        Responds with status 200/401.

        Args:
            data (dict): A dictionary having the user/token.
            request (aiohttp.web_request.Request): Request of type GET /REP/incomplete.

        Returns:
            aiohttp.web_response.Response: A response which includes a dictionary of pages for
            incomplete exams.
        """

        if not data["user"] in ("manager", "scanner"):
            return web.Response(status=401)
        # The response is a dictionary of the form:
        # {test_number: [[test string, TODO: Version number ?, True/False for page incomplete or not], ...], ...}
        # Ex: {1: [['t.1', 1, True], ['t.2', 1, True], ['t.3', 2, True], ['t.4', 1, True], ['t.5', 2, True], ['t.6', 2, False]]}
        return web.json_response(self.server.RgetIncompleteTests(), status=200)

    # @routes.get("/REP/dangling")p
    @authenticate_by_token_required_fields(["user"])
    def getDanglingPages(self, data, request):
        """Respond with the list of dangling pages - pages attached to groups that are not complete.

        Responds with status 200/401.

        Args:
            data (dict): A dictionary having the user/token.
            request (aiohttp.web_request.Request): Request of type GET /REP/incomplete.

        Returns:
            aiohttp.web_response.Response: A response which includes a list of dictionaries of pages that belong
            to incomplete groups (ie not completely scanned, and not ID'd or marked)
        """

        if not data["user"] in ("manager", "scanner"):
            return web.Response(status=401)
        # The response is a list of dictionaries of the form:
        # [
        # {'test': number, 'type': 'tpage', 'page': number, 'code': blah, 'group': blah},
        # {'test': number, 'type': 'hwpage', 'order': number, 'code': blah, 'group': blah},
        # {'test': number, 'type': 'expage', 'order': number, 'code': blah, 'group': blah}
        # ]
        return web.json_response(self.server.getDanglingPages(), status=200)

    # @routes.get("/REP/completeHW")
    @authenticate_by_token_required_fields(["user"])
    def RgetCompleteHW(self, d, request):
        if not d["user"] in ("manager", "scanner"):
            return web.Response(status=401)
        return web.json_response(self.server.RgetCompleteHW(), status=200)

    # @routes.get("/REP/missingHW")
    @authenticate_by_token_required_fields(["user"])
    def RgetMissingHWQ(self, d, request):
        if not d["user"] in ("manager", "scanner"):
            return web.Response(status=401)
        return web.json_response(self.server.RgetMissingHWQ(), status=200)

    # @routes.get("/REP/unused")
    @authenticate_by_token_required_fields(["user"])
    def RgetUnusedTests(self, d, request):
        # TODO: Requires documentation.
        if not d["user"] in ("manager", "scanner"):
            return web.Response(status=401)
        return web.json_response(self.server.RgetUnusedTests(), status=200)

    # @routes.get("/REP/progress")
    @authenticate_by_token_required_fields(["user", "q", "v"])
    def RgetProgress(self, data, request):
        """Respond with an overall progress status of the marking process.

        Responds with status 200/401.

        Args:
            data (dict): Dictionary including user data in addition to question number and version.
            request (aiohttp.web_request.Request): Request of type GET /REP/progress.

        Returns:
            aiohttp.web_response.Response: A response which includes a dictionary of pages for
            incomplete exams.
        """

        # An example of the report sent as a response:  TODO: Should I explain this better.
        # {'NScanned': 10, 'NMarked': 7, 'NRecent': 7, 'avgMark': 4.428571428571429, 'avgMTime': 153.57142857142858}
        if not data["user"] == "manager":
            return web.Response(status=401)
        return web.json_response(
            self.server.RgetProgress(self.server.testSpec, data["q"], data["v"]),
            status=200,
        )

    # @routes.get("/REP/questionUserProgress")
    @authenticate_by_token_required_fields(["user", "q", "v"])
    def RgetQuestionUserProgress(self, data, request):
        """Respond with information on each user's progress on grading of a question version.

        Responds with status 200/401.

        Args:
            data (dict): Dictionary including user data in addition to question number and version.
            request (aiohttp.web_request.Request): Request GET /REP/questionUserProgress.

        Returns:
            aiohttp.web_response.Response: A response with information on the progress of each
            use on each question.
        """

        if not data["user"] == "manager":
            return web.Response(status=401)

        # A list of list with the following response:
        # [ Number of scanned papers, [Username, Number of marked], [Username, Number of marked], etc]
        return web.json_response(
            self.server.RgetQuestionUserProgress(data["q"], data["v"]), status=200
        )

    # @routes.get("/REP/markHistogram")
    @authenticate_by_token_required_fields(["user", "q", "v"])
    def RgetMarkHistogram(self, data, request):
        """Returns histogram info for the grading of a question.

        Responds with status 200/401.

        Args:
            data (dict): Dictionary including user data in addition to question number.
            request (aiohttp.web_request.Request): Request of type GET /REP/markHistogram.

        Returns:
            aiohttp.web_response.Response: A response object with the grading histogram info
            for a question.
        """

        if not data["user"] == "manager":
            return web.Response(status=401)
        # Respond with the corresponding values for non-zero bars in the histogram.
        # A dictionary with usernames as keys and the bar values for non zero bars as dictionaries.
        # TODO: What did the columns represent ?
        # Example: {'user0': {5: 3, 4: 1}}
        return web.json_response(
            self.server.RgetMarkHistogram(data["q"], data["v"]), status=200
        )

    @authenticate_by_token_required_fields(["user"])
    def RgetIdentified(self, data, request):
        """Respond with a dictionary of identified papers

        Responds with status 200/401.

        Args:
            data (dict): A dictionary having the user/token.
            request (aiohttp.web_request.Request): GET /REP/identified request type.

        Returns:
            aiohttp.web_response.Response: A response object including a dictionary of
            identified papers.
        """

        if not data["user"] == "manager":
            return web.Response(status=401)
        return web.json_response(self.server.RgetIdentified(), status=200)

    @authenticate_by_token_required_fields(["user"])
    def RgetNotAutoIdentified(self, data, request):
        """Respond with a dictionary of scanned but not auto-id'd papers

        Responds with status 200/401.

        Args:
            data (dict): A dictionary having the user/token.
            request (aiohttp.web_request.Request): GET /REP/unidentified request type.

        Returns:
            aiohttp.web_response.Response: A response object including a dictionary of scanned but not auto-id'd papers.
        """

        if not data["user"] == "manager":
            return web.Response(status=401)
        return web.json_response(self.server.RgetNotAutoIdentified(), status=200)

    # @routes.get("/REP/completionStatus")
    @authenticate_by_token_required_fields(["user"])
    def RgetCompletionStatus(self, data, request):
        """Respond with a status of the complete papers providing information on grading progress.

        Responds with status 200/401.

        Args:
            data (dict): A dictionary having the user/token.
            request (aiohttp.web_request.Request): Request of type GET /REP/completionStatus.

        Returns:
            aiohttp.web_response.Response: a dictionary keyed by test
            number (str), where the values are a 3-list:
            `[is_scanned, is_identified, number_of_questions_marked]`.
        """

        if not data["user"] == "manager":
            return web.Response(status=401)
        return web.json_response(self.server.RgetCompletionStatus(), status=200)

    # @routes.get("/REP/outToDo")
    @authenticate_by_token_required_fields(["user"])
    def RgetOutToDo(self, data, request):
        """Respond with a list of tasks that are currently out with clients.

        Args:
            data (dict): A dictionary having the user/token.
            request (aiohttp.web_request.Request): GET /REP/outToDo type request.

        Returns:
            aiohttp.web_response.Response: A response that includes a list of todo
            tasks.
        """

        if not data["user"] == "manager":
            return web.Response(status=401)

        # Response includes a list of [task code, username, time of task sent out].
        # Ex: [['mrk-t11-q1-v1', 'user0', '20:06:21-01:21:47'], ... ]
        return web.json_response(self.server.RgetOutToDo(), status=200)

    # @routes.get("/REP/status/{test}")
    @authenticate_by_token_required_fields(["user"])
    def RgetStatus(self, data, request):
        """Respond with the marking status of an exam.

        Responds with status 200/401/404.

        Args:
            data (dict): A dictionary having the user/token.
            request (aiohttp.web_request.Request): Request of typeGET /REP/status/2 which also
                includes the test number.

        Returns:
            aiohttp.web_response.Response: A response including a dictionary for information on
            grading status for an exam.
        """

        if not data["user"] == "manager":
            return web.Response(status=401)
        test_number = request.match_info["test"]
        marking_status_response = self.server.RgetStatus(test_number)
        status_response_success = marking_status_response[0]

        # An example of gradding status summary can be seen below:
        #  {'number': 2, 'identified': True, 'marked': False, 'totalled': False, 'sid': '10130103', 'sname': 'Vandeventer, Irene',
        # 'iwho': 'HAL', 1: {'marked': False, 'version': 2}, 2: {'marked': False, 'version': 1}, 3: {'marked': False, 'version': 2}}
        # TODO: What is iwho ?
        if status_response_success:
            marking_status_dict = marking_status_response[1]
            return web.json_response(marking_status_dict, status=200)
        else:
            return web.Response(status=404)

    # @routes.get("/REP/spreadsheet")
    @authenticate_by_token_required_fields(["user"])
    @readonly_admin
    def RgetSpreadsheet(self, data, request):
        """Information used to create a spreadsheet during or post-grading.

        Responds with status 200/401/403.

        Args:
            data (dict): A dictionary having the user/token.
            request (aiohttp.web_request.Request): Request of type GET /REP/spreadsheet.

        Returns:
            aiohttp.web_response.Response: Information needed to build the
            grading results spreadsheet.
            The result is a large dict, keyed by paper number (integer but
            here a string).  The value for each paper is another dict::

                {
                    "1": {
                       'identified': True,
                       'marked': False,
                       'sid': '12345678',
                       'sname': 'Fink, Iris',
                       'q1v': 2, 'q1m': 3,
                       'q2v': 1, 'q2m': '',
                       'q3v': 2, 'q3m': '',
                       'last_update': '2022-05-13T21:15:02.072122+00:00'
                    },
                    "2": {
                       ...
                    }
                }

            Notable here is ``q1v`` which is "Question 1 version" (an integer),
            and ``q1m`` which is "Question 1 mark", an integer or the empty
            string if the question is still being marked (``marked`` should be
            `False` in this case).
        """
        r = self.server.RgetSpreadsheet()
        return web.json_response(r, status=200)

    # @routes.get("/REP/coverPageInfo/{test}")
    @authenticate_by_token_required_fields(["user"])
    def RgetCoverPageInfo(self, d, request):
        # TODO: Requires documentation.
        if not d["user"] == "manager":
            return web.Response(status=401)
        testNumber = request.match_info["test"]
        rmsg = self.server.RgetCoverPageInfo(testNumber)
        return web.json_response(rmsg, status=200)

    # @routes.get("/REP/originalFiles/{test}")
    @authenticate_by_token_required_fields(["user"])
    def RgetOriginalFiles(self, d, request):
        # TODO: Requires documentation.
        if not d["user"] == "manager":
            return web.Response(status=401)
        testNumber = request.match_info["test"]
        rmsg = self.server.RgetOriginalFiles(testNumber)

        if len(rmsg) > 0:
            return web.json_response(rmsg, status=200)
        else:
            return web.Response(status=404)

    # @routes.get("/REP/userList")
    @authenticate_by_token_required_fields(["user"])
    def RgetUserList(self, data, request):
        """Return a list of Plom users.

        Responds with status 200/401.

        Args:
            data (dict): A dictionary having the user/token.
            request (aiohttp.web_request.Request): Request of type GET /REP/userList.

        Returns:
            aiohttp.web_response.Response: A response object entailing a list of Plom users.
        """

        if not data["user"] == "manager":
            return web.Response(status=401)

        return web.json_response(self.server.RgetUserList(), status=200)

    # @routes.get("/REP/userDetails")
    @authenticate_by_token_required_fields(["user"])
    def RgetUserDetails(self, data, request):
        """Gets a list of users and their detail.

        Responds with status 200/401.

        Args:
            data (dict): A dictionary having the user/token.
            request (aiohttp.web_request.Request): Request GET /REP/userDetails.

        Returns:
            aiohttp.web_response.Response: A response object entailing a list of plom users.
        """

        if not data["user"] == "manager":
            return web.Response(status=401)

        # A list of list for each user involving the following format:
        # [ Username, User enabled, User logged in, Last activity time, Last action,
        #   Papers ID'd by user, Papers totalled by user, Question's marked by user]
        return web.json_response(self.server.RgetUserDetails(), status=200)

    # @routes.get("/REP/markReview")
    @authenticate_by_token_required_fields(
        [
            "user",
            "filterPaperNumber",
            "filterQ",
            "filterV",
            "filterUser",
            "filterMarked",
        ]
    )
    @readonly_admin
    def RgetMarkReview(self, data, request):
        """Respond with a list of graded tasks that match the filter description.

        Args:
            data (dict): A dictionary which includes the user data in addition to the
                filter query information sent by the client.
            request (aiohttp.web_request.Request): Request of type GET /REP/markReview.

        Returns:
            aiohttp.web_response.Response: JSON of a list of lists of the form
            [Test number, Question number, Version number, Mark, Username, seconds spent marking, date/time of marking, tags].
            For example: ``[[3, 1, 1, 5, 'user0', 7, '20:06:21-01:21:56', ''], [...]]``.
            Can fail with 401/403 for authentication problems.
        """
        matches = self.server.RgetMarkReview(
            filterPaperNumber=data["filterPaperNumber"],
            filterQ=data["filterQ"],
            filterV=data["filterV"],
            filterUser=data["filterUser"],
            filterMarked=data["filterMarked"],
        )
        return web.json_response(matches, status=200)

    # @routes.get("/REP/idReview")
    @authenticate_by_token_required_fields(["user"])
    def RgetIDReview(self, data, request):
        """Respond with metadata about identified papers.

        Responds with status 200/401.

        Args:
            data (dict): A dictionary having the user/token.
            request (aiohttp.web_request.Request): Request of type GET /REP/idReview.

        Returns:
            aiohttp.web_response.Response: A response including metadata about the identified
            papers queued for reviewing.
        """

        if not data["user"] == "manager":
            return web.Response(status=401)
        rmsg = self.server.RgetIDReview()

        # A list of lists included information of format below:
        # [Test number, User who ID'd the paper, Time of ID'ing, Student ID, Student name]
        return web.json_response(rmsg, status=200)

    # @routes.get("/REP/fileAudit")
    @authenticate_by_token_required_fields(["user"])
    def getFilesInAllTests(self, data, request):
        """Respond with metadata about image-files used in all tests.

        In particular, for each test, which imagefiles/bundles are used
        for each id-group, dnm-group, and question-group.

        Responds with status 200/401/403.

        Args:
            data (dict): A dictionary having the user/token.
            request (aiohttp.web_request.Request): Request of type GET /REP/idReview.

        Returns:
            aiohttp.web_response.Response: A response including metadata about the files used.
        """

        if not data["user"] == "manager":
            raise web.HTTPForbidden(reason="I want to speak to the manager")
        rmsg = self.server.getFilesInAllTests()

        return web.json_response(rmsg, status=200)

    def setUpRoutes(self, router):
        """Adds the response functions to the router object.

        Args:
            router (aiohttp.web_urldispatcher.UrlDispatcher): Router object which we will add the
                response functions to.
        """
        router.add_get("/REP/scanned", self.RgetScannedTests)
        router.add_get("/REP/incomplete", self.RgetIncompleteTests)
        router.add_get("/REP/dangling", self.getDanglingPages)
        router.add_get("/REP/completeHW", self.RgetCompleteHW)
        router.add_get("/REP/missingHW", self.RgetMissingHWQ)
        router.add_get("/REP/unused", self.RgetUnusedTests)
        router.add_get("/REP/progress", self.RgetProgress)
        router.add_get("/REP/questionUserProgress", self.RgetQuestionUserProgress)
        router.add_get("/REP/markHistogram", self.RgetMarkHistogram)
        router.add_get("/REP/identified", self.RgetIdentified)
        router.add_get("/REP/notautoid", self.RgetNotAutoIdentified)
        router.add_get("/REP/completionStatus", self.RgetCompletionStatus)
        router.add_get("/REP/outToDo", self.RgetOutToDo)
        router.add_get("/REP/status/{test}", self.RgetStatus)
        router.add_get("/REP/spreadsheet", self.RgetSpreadsheet)
        router.add_get("/REP/originalFiles/{test}", self.RgetOriginalFiles)
        router.add_get("/REP/coverPageInfo/{test}", self.RgetCoverPageInfo)
        router.add_get("/REP/userList", self.RgetUserList)
        router.add_get("/REP/userDetails", self.RgetUserDetails)
        router.add_get("/REP/markReview", self.RgetMarkReview)
        router.add_get("/REP/idReview", self.RgetIDReview)
        router.add_get("/REP/filesInAllTests", self.getFilesInAllTests)
