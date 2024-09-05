# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020-2021, 2023-2024 Colin B. Macdonald

import plom.plom_exceptions
from plom.plom_exceptions import PlomException, PlomAuthenticationException
from plom.plom_exceptions import *  # noqa


def test_plom_exc_string() -> None:
    e = PlomException("foo")
    assert str(e) == "foo"


def test_exc_inheritance() -> None:
    e = PlomAuthenticationException()
    assert isinstance(e, PlomException)


def test_exc_auth_has_default_msg() -> None:
    e = PlomAuthenticationException()
    assert "authenticate" in str(e).lower()
    e = PlomAuthenticationException("foo")
    assert str(e) == "foo"


def test_exc_all_print_properly() -> None:
    excs = [eval(e) for e in dir(plom.plom_exceptions) if e.startswith("Plom")]
    assert len(excs) > 10  # we have some exceptions
    for exc in excs:
        assert str(exc("foo")) == "foo"
