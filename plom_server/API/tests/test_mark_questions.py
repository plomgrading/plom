# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Bryan Tanady

# pytest
import pytest
import pytest_mock

# rest_framework
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APIClient


# plom_server
from plom_server.Papers.models import Paper
from plom_server.Mark.models import MarkingTask, MarkingTaskTag
from plom_server.Mark.services import (
    MarkingTaskService,
    page_data,
)

# misc
from django.core.files.uploadedfile import SimpleUploadedFile
from typing import Any
import json


@pytest.mark.usefixtures("marking_test_setup")
class TestMarkQuestionAPI:

    @pytest.fixture(autouse=True)
    def setup(self, marking_test_setup) -> None:
        """For each testcase we call this setup."""
        self.non_auth_client: APIClient = marking_test_setup["non_auth_client"]
        self.auth_client: APIClient = marking_test_setup["auth_client"]
        self.paper: Paper = marking_test_setup["paper"]
        self.task: MarkingTask = marking_test_setup["task"]
        self.tag: MarkingTaskTag = marking_test_setup["tag"]

    # ================== MarkTaskNextAvailable(APIView) test =============================
    def test_get_next_available(self):
        """Test GET: /MK/tasks/available endpoint with valid params.

        This test case verifies when there's unclaimed task and:
            a. It returns 200 (SUCCESS) status.
            b. It returns the taskcode (identified as "code" attribute)
                of the task returned by the service level.
        """
        # make the GET API call with params
        url = reverse("api_mark_task_next")
        resp = self.auth_client.get(
            url, {"q": self.task.question_index, "tags": "foo, bar"}
        )

        # check status code
        assert resp.status_code == status.HTTP_200_OK

        # check it returns the task code
        assert resp.json() == self.task.code

    # ================== MarkTask(APIView) test =============================

    def test_claim_task_invalid_code(self):
        """Test PATCH: /MK/tasks/{code} with invalid code format."""
        code = "q1c2"
        url = reverse("api_mark_task", kwargs={"code": code})
        resp = self.auth_client.patch(url)
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_claim_non_existent_task(self):
        """Test PATCH: /MK/tasks/{code} for non-existent task."""
        code = "q1g1"
        url = reverse("api_mark_task", kwargs={"code": code})
        resp = self.auth_client.patch(url)
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_claim_task_valid_code(
        self,
        mocker: pytest_mock.MockerFixture,
    ):
        """Test PATCH: /MK/tasks/{code} with valid code.

        This test implicitly enforces question_data is obtained from page_data.get_question_pages_list.

        This test verifies:
            a. On success, the API returns [question_data, tags, task.pk] and 200 status.
            b. If attempting to claim an assigned task return a 409 (CONFLICT) status.
        """
        # mock page_data.get_question_pages_list that provides question_data
        dummy_question_data: dict[str, Any] = {"a": 1, "b": 2}

        mocker.patch.object(
            page_data,
            page_data.get_question_pages_list.__name__,
            return_value=dummy_question_data,
        )

        # attempt to claim that task
        url = reverse("api_mark_task", kwargs={"code": self.task.code})
        resp = self.auth_client.patch(url)

        # ensure 200 status
        assert resp.status_code == status.HTTP_200_OK

        # ensure correct return format as documented in the API
        assert resp.json() == [dummy_question_data, [self.tag.text], self.task.pk]

        # attempt to reclaim that task
        url = reverse("api_mark_task", kwargs={"code": self.task.code})
        auth_client: APIClient = self.auth_client
        resp = auth_client.patch(url)

        # ensure 409 status
        assert resp.status_code == status.HTTP_409_CONFLICT

    def test_submit_malformed_input(self, mocker: pytest_mock.MockerFixture):
        """Test POST: /MK/tasks/{code} with incorrect code formatting."""
        incorrect_code = "q1q2"
        url = reverse("api_mark_task", kwargs={"code": incorrect_code})

        # Prepare mock file
        payload = {"dummy": ["data"]}
        dummy_file = SimpleUploadedFile(
            "sample.plom",
            json.dumps(payload).encode("utf-8"),
            content_type="application/json",
        )

        # Make a stub for validate_and_clean_marking_data function
        fake_cleaned_data: dict = {}
        fake_annot_data: dict = {}
        mocker.patch.object(
            MarkingTaskService,
            MarkingTaskService.validate_and_clean_marking_data.__name__,
            return_value=(fake_cleaned_data, fake_annot_data),
        )

        response = self.auth_client.post(
            url,
            {"plomfile": dummy_file, "annotation_image": dummy_file, "md5sum": 1},
            format="multipart",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    # ============== Integration of MarkTaskNextAvailable(APIView) MarkTask(APIView) test =================

    def test_get_zero_task(self):
        """Test GET: /MK/tasks/available when all tasks have been claimed."""
        # first test to get available task
        url = reverse("api_mark_task_next")
        resp = self.auth_client.get(url, {"q": self.task.question_index})
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json() == self.task.code

        # claim the only one task in the setup
        url = reverse("api_mark_task", kwargs={"code": self.task.code})
        resp = self.auth_client.patch(url, {"version": 0})
        assert resp.status_code == status.HTTP_200_OK

        # now get the task again
        url = reverse("api_mark_task_next")
        resp = self.auth_client.get(url, {"q": self.task.question_index})
        assert resp.status_code == status.HTTP_204_NO_CONTENT
