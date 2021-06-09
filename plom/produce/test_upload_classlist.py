# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020 Dryden S. Wiebe
# Copyright (C) 2020 Colin B. Macdonald

from unittest.mock import MagicMock

from plom.messenger import ManagerMessenger
from plom.plom_exceptions import PlomExistingLoginException, PlomConflict

from plom.produce import upload_classlist


def test_produce_upload_classlist():
    classlist = [(10050380, "Fink, Iris")]

    msgr = ManagerMessenger()
    msgr.upload_classlist = MagicMock(return_value=None)
    msgr.closeUser = MagicMock(return_value=None)
    msgr.stop = MagicMock(return_value=None)

    upload_classlist(classlist=classlist, msgr=msgr)

    msgr.upload_classlist.assert_called_with(classlist)
    msgr.closeUser.assert_called()
    msgr.stop.assert_called()
