# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020 Dryden S. Wiebe
# Copyright (C) 2020-2022, 2024 Colin B. Macdonald

from unittest.mock import MagicMock

from plom.messenger import ManagerMessenger

from plom.create.upload_classlist import _raw_upload_classlist


def test_produce_upload_classlist() -> None:
    classlist = [{"id": 10050380, "name": "Fink, Iris"}]
    expected_call_cl = classlist

    msgr = ManagerMessenger()
    msgr.upload_classlist = MagicMock(return_value=None)  # type: ignore
    msgr.closeUser = MagicMock(return_value=None)  # type: ignore
    msgr.stop = MagicMock(return_value=None)  # type: ignore

    _raw_upload_classlist(classlist=classlist, msgr=msgr)

    msgr.upload_classlist.assert_called_with(expected_call_cl, False)
    msgr.closeUser.assert_called()
    msgr.stop.assert_called()
