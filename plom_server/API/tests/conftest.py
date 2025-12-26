# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Bryan Tanady
# Copyright (C) 2025 Colin B. Macdonald

"""conftest.py is a default configuration file for Pytest.

We use it to define resources that are shared across API testcases.
"""

import os
from typing import Any

import django
import pytest
from rest_framework.test import APIClient

from plom_server.Authentication.services import AuthService
from plom_server.Base.models import User
from plom_server.Papers.models import Paper
from plom_server.Mark.models import MarkingTask, MarkingTaskTag


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "plom_server.settings")
django.setup()


@pytest.fixture
def api_client() -> APIClient:
    """Represents a non-authenticated client.

    Returns:
        A non-authenticated APIClient.
    """
    return APIClient()


@pytest.fixture
def user(db):
    """Creates and returns a fresh Django user that is a "marker".

    Args:
        db: pytest-django fixture that provides database access.

    Returns:
        A new User instance saved to the test database.
    """
    AuthService.create_groups()
    username, __ = AuthService.create_user_and_add_to_group("alice", "marker")
    return User.objects.get(username=username)


@pytest.fixture
def auth_client(api_client: APIClient, user: User) -> APIClient:
    """Represents an authenticated client.

    Args:
        api_client: a non-authenticated APIClient.
        user: django app user.

    Returns:
        An authenticated APIClient.
    """
    api_client.force_authenticate(user=user)
    return api_client


@pytest.fixture
def minimum_test_setup(
    db, api_client: APIClient, auth_client: APIClient
) -> dict[str, Any]:
    """This setup minimum environment for testing.

    Returns:
        A dict with these keys: [non_auth_client, auth_client, paper]
    """
    paper = Paper.objects.create(paper_number=1)
    return {"non_auth_client": api_client, "auth_client": auth_client, "paper": paper}


@pytest.fixture
def marking_test_setup(db, minimum_test_setup: dict[str, Any]) -> dict[str, Any]:
    """This setup minimum environment for marking API testing.

    Current environment contains each of [non_auth_client, auth_client, paper, task, tag].
        1. Paper has paper_number 1.
        2. task is for paper_number=1 question_index=2
        3. tag is for the above task.

    Returns:
        A dict with these keys: [non_auth_client, auth_client, paper, task, tag].
    """
    task = MarkingTask.objects.create(
        paper=minimum_test_setup["paper"],
        question_index=2,
        question_version=1,
        code="0001g2",
    )
    tag = MarkingTaskTag.objects.create(text="tag")
    tag.task.add(task)
    tag.save()

    result = minimum_test_setup.copy()
    result.update({"task": task, "tag": tag})
    return result
