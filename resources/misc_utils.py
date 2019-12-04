# -*- coding: utf-8 -*-

"""Misc utilities"""

__author__ = "Colin B. Macdonald, Omer Angel"
__copyright__ = "Copyright (C) 2019 Colin B. Macdonald, Omer Angel"
__license__ = "AGPL-3.0-or-later"
# SPDX-License-Identifier: AGPL-3.0-or-later

def format_int_list_with_runs(L):
    """Replace runs in a list with a range notation"""
    L = set(map(int, L))
    M = max(L)
    start = None
    r = ""
    for i in range(-1, M + 2):
        if start is None and i in L:  # run start
            start = i
            r = r + str(i)
        elif start is not None and i not in L:  # run ended
            if i > start + 1:
                r = r + "–" + str(i - 1)
            if i < M:  # not last run
                r = r + ", "
            start = None
    return r


def test1():
    L = ['1', '2', '3', '4', '7', '10', '11', '12', '13', '14', '64']
    out = "1–4, 7, 10–14, 64"
    assert format_int_list_with_runs(L) == out
