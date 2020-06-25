import os
from aiohttp import web, MultipartWriter, MultipartReader

from .routeutils import authenticate_by_token, authenticate_by_token_required_fields


class TotalHandler:
    def __init__(self, plomServer):
        self.server = plomServer
    
    # TODO: I Think this one is supposed to me MaxMark not MarkMark
    # @routes.get("/TOT/maxMark")
    @authenticate_by_token
    def TgetMarkMark(self):
        """Respond with the maximum total possible score for the exam.

        Respond with status 200.

        Returns:
            aiohttp.web_response.Response: Response object which has the
                maximum mark for the question.
        """
        return web.json_response(self.server.TgetMaxMark(), status=200)

    # @routes.get("/TOT/progress")
    @authenticate_by_token
    def TprogressCount(self):
        """Respond with the number of done tasks and total number of tasks.

        Respond with status 200.

        Returns:
            aiohttp.web_response.Response: Response object which has a list 
                of number of done tasks and total number of tasks.
        """
        return web.json_response(self.server.TprogressCount(), status=200)

    # @routes.get("/TOT/tasks/complete")
    @authenticate_by_token_required_fields(["user"])
    def TgetDoneTasks(self, data, request):
        """Respond with a list of totalled exam names and total scores.

        Respond with status 200.

        Args:
            data (dict): Includes the user/token for authentication.
            request (aiohttp.web_request.Request): A request of type PATCH /TOT/tasks/`task number`.

        Returns:
            aiohttp.web_response.Response: A response object which includes the lists 
                of lists including the [test_number, total_score].
        """
        # return the completed list
        return web.json_response(self.server.TgetDoneTasks(data["user"]), status=200)

    # @routes.get("/TOT/image/{test}")
    @authenticate_by_token_required_fields(["user"])
    def TgetImage(self, data, request):
        """Respond with the image of the totalled task.

        For example, used by the manager to retreive the totalled page's image.
        Respond with status 200/409.

        Args:
            data (dict): Includes the user/token for authentication.
            request (aiohttp.web_request.Request): Request of type 
                GET /TOT/image/'test_number'

        Returns:
            aiohttp.web_fileresponse.FileResponse: Respond with path 
                of the tasks images.
        """
        test = request.match_info["test"]
        get_image_response = self.server.TgetImage(data["user"], test)
        get_image_status = get_image_response[0]

        if get_image_status:  # user allowed access - returns [true, fname0]
            task_image_path = get_image_response[1]
            return web.FileResponse(task_image_path, status=200)
        else:
            return web.Response(status=409)  # someone else has that image

    # @routes.get("/TOT/tasks/available")
    @authenticate_by_token
    def TgetNextTask(self):
        """Respond with the next exam/task number.

        Respond with status 200/204.

        Returns:
            aiohttp.web_response.Response: A response object with the
                paper number for the next task.
        """

        next_task_data = self.server.TgetNextTask()  # returns [True, code] or [False]
        next_task_available = next_task_data[0]

        if next_task_available:
            next_task_number = next_task_data[1]
            return web.json_response(next_task_number, status=200)
        else:
            return web.Response(status=204)  # no papers left

    # @routes.patch("/TOT/tasks/{task}")
    @authenticate_by_token_required_fields(["user"])
    def TclaimThisTask(self, data, request):
        """Respond with the path image for a paper for totalling.

        Respond with status 200/204.

        Args:
            data (dict): Includes the user/token for authentication.
            request (aiohttp.web_request.Request): Request of type 
                PATCH /TOT/tasks/`task_number` which also includes 
                the task numbers.

        Returns:
            aiohttp.web_fileresponse.FileResponse: A request object that 
                includes the path to the claimed task image.
        """
        test_number = request.match_info["task"]
        task_claim_status = self.server.TclaimThisTask(data["user"], test_number)
        task_claim_success = task_claim_status[0]

        if task_claim_success:  # user allowed access - returns [true, fname0]
            task_image_path = task_claim_status[1]
            return web.FileResponse(task_image_path, status=200)
        else:
            return web.Response(status=204)  # that task already taken.

    # @routes.put("/TOT/tasks/{task}")
    @authenticate_by_token_required_fields(["user", "mark"])
    def TreturnTotalledTask(self, data, request):
        """Saves the mark of the totalled task to the database.

        Respond with status 200/404.

        Args:
            data (dict): Includes the user/token for authentication in 
                addition to the total task mark.
            request (aiohttp.web_request.Request): Request of type 
                PUT /TOT/tasks/`task_number` which includes the
                task number.

        Returns:
            aiohttp.web_response.Response: Empty response to indicate 
                total grade saving success or failure. 
        """
        test_number = request.match_info["task"]


        totalled_task_response = self.server.TreturnTotalledTask(data["user"], test_number, data["mark"])
        total_saved_success = totalled_task_response[0]

        if total_saved_success:  # all good
            return web.Response(status=200)
        else:  # a more serious error - can't find this in database
            return web.Response(status=404)

    # @routes.delete("/TOT/tasks/{task}")
    @authenticate_by_token_required_fields(["user"])
    def TdidNotFinish(self, data, request):
        """Respond with the unfinished totalling task exam number.

        This could occur for example when the client closes with unfinished totalling tasks.
        Respond with status 200.

        Args:
            data (dict): Includes the user/token for authentication.
            request (aiohttp.web_request.Request): Request DELETE /TOT/tasks/`task_number`
                which includes the unfinished task number.

        Returns:
            aiohttp.web_response.Response: An empty response object to
                indicate success.
        """
        test_number = request.match_info["task"]
        self.server.TdidNotFinish(data["user"], test_number)
        return web.json_response(status=200)

    # @routes.patch("/TOT/review")
    @authenticate_by_token_required_fields(["testNumber"])
    def TreviewTotal(self, data, request):
        """Responds with an empty response object indicating if the review Total is possible and the document exists.

        Responds with status 200/404.

        Args:
            data (dict): A dictionary having the user/token in addition to the `testNumber`.
            request (aiohttp.web_request.Request): Request of type PATCH /TOT/review.

        Returns:
            aiohttp.web_fileresponse.FileResponse: An empty response indicating the availability status of
                the review document.
        """

        if self.server.TreviewTotal(data["testNumber"]):
            return web.Response(status=200)
        else:
            return web.Response(status=404)

    def setUpRoutes(self, router):
        """Adds the response functions to the router object.

        Args:
            router (aiohttp.web_urldispatcher.UrlDispatcher): Router object which we will add the response functions to.
        """
        
        router.add_get("/TOT/maxMark", self.TgetMarkMark)
        router.add_get("/TOT/progress", self.TprogressCount)
        router.add_get("/TOT/tasks/complete", self.TgetDoneTasks)
        router.add_get("/TOT/image/{test}", self.TgetImage)
        router.add_get("/TOT/tasks/available", self.TgetNextTask)
        router.add_patch("/TOT/tasks/{task}", self.TclaimThisTask)
        router.add_put("/TOT/tasks/{task}", self.TreturnTotalledTask)
        router.add_delete("/TOT/tasks/{task}", self.TdidNotFinish)
        router.add_patch("/TOT/review", self.TreviewTotal)
