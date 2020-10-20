# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2019-2020 Colin B. Macdonald
# Copyright (C) 2020 Dryden Wiebe

from .utils import my_hash, rand_hex


def test_hash():
    assert my_hash("12345678", salt="salt", digits=12) == "351525727036"
    assert my_hash("12345678", salt="salty", digits=12) == "782385405730"
    assert my_hash("12345679", salt="salt", digits=12) == "909470548567"


def test_hash_error():
    error = None
    try:
        my_hash("123456789", salt=None)
        error = False
    except ValueError:
        error = True
    assert error == True


def test_hex_code():
    assert rand_hex().isalnum()
    assert len(rand_hex(1)) == 1
    assert len(rand_hex(2)) == 2
    assert len(rand_hex(32)) == 32
