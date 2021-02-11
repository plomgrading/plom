# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2021 Colin B. Macdonald

from pytest import raises
from plom.messenger import Messenger
from plom.plom_exceptions import PlomBenignException


def test_invalid_url_too_many_colons():
    m = Messenger("example.com:1234:1234")
    raises(PlomBenignException, lambda: m.start())
