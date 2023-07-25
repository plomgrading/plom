# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2021, 2023 Colin B. Macdonald

from pytest import raises
from plom.messenger import Messenger


def test_invalid_url_too_many_colons():
    with raises(Exception):
        m = Messenger("example.com:1234:1234")
        m.start()
