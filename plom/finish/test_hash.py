# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2019-2020 Colin B. Macdonald
# Copyright (C) 2020 Dryden Wiebe

from pytest import raises

from .utils import rand_hex, rand_integer_code
from .utils import salted_int_hash_from_str as my_hash
from .utils import salted_hex_hash_from_str as hex_hash


def test_hash():
    assert my_hash("12345678", salt="salt", digits=12) == "351525727036"
    assert my_hash("12345678", salt="salty", digits=12) == "782385405730"
    assert my_hash("12345679", salt="salt", digits=12) == "909470548567"


def test_hex_code():
    assert rand_hex().isalnum()
    assert len(rand_hex(1)) == 1
    assert len(rand_hex(2)) == 2
    assert len(rand_hex(32)) == 32


def test_int_code():
    assert isinstance(rand_integer_code(), int)
    assert rand_integer_code(10) > 10


def test_hex_hash_defaults():
    assert len(hex_hash("12345678", salt="salt")) == 16


def test_hash_no_default_salt():
    assert raises(ValueError, lambda: hex_hash("12345678"))
    assert raises(ValueError, lambda: my_hash("123456789"))


def test_hex_hash():
    assert hex_hash("12345678", salt="salt", digits=4) == "1fbe"
    assert hex_hash("12345678", salt="salt", digits=8) == "1fbef050"
    assert hex_hash("12345678", salt="salt", digits=9) == "1fbef0509"
