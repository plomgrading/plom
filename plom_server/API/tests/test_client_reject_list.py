# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Colin B. Macdonald

from packaging.version import Version

from django.test import TestCase
from ..views.server_info import _client_reject_list


class TestsClientRejectList(TestCase):

    def test_reject_list_key_validity(self) -> None:
        lst = _client_reject_list()
        for entry in lst:
            for x in entry.keys():
                assert isinstance(x, str)
                assert x in ("client-id", "version", "operator", "reason", "action")

    def test_reject_list_action_operator_validity(self) -> None:
        lst = _client_reject_list()
        for entry in lst:
            act = entry.get("action")
            assert act in (None, "warn", "block")
            op = entry.get("operator")
            assert op in (None, "==", "<=", ">=", "<", ">")

    def test_reject_list_version_parses(self) -> None:
        lst = _client_reject_list()
        for entry in lst:
            ver = entry["version"]
            Version(ver)
