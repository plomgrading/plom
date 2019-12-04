# -*- coding: utf-8 -*-

"""Misc utilities"""

__author__ = "Colin B. Macdonald, Omer Angel"
__copyright__ = "Copyright (C) 2019 Colin B. Macdonald, Omer Angel"
__license__ = "AGPL-3.0-or-later"
# SPDX-License-Identifier: AGPL-3.0-or-later

import math


def format_int_list_with_runs(L):
    """Replace runs in a list with a range notation"""
    L = _find_runs(L)
    L = _flatten_2len_runs(L)
    L = ["{}–{}".format(l[0], l[-1]) if isinstance(l, list) else str(l) for l in L]
    return ", ".join(L)


def _find_runs(S):
    S = [int(x) for x in S]
    S.sort()
    L = []
    prev = -math.inf
    for x in S:
        if x - prev == 1:
            run.append(x)
        else:
            run = [x]
            L.append(run)
        prev = x
    return L


def _flatten_2len_runs(L):
    L2 = []
    for l in L:
        if len(l) < 3:
            L2.extend(l)
        else:
            L2.append(l)
    return L2


# TODO: unit tests
def test1():
    L = ['1', '2', '3', '4', '7', '10', '11', '12', '13', '14', '64']
    out = "1–4, 7, 10–14, 64"
    assert format_int_list_with_runs(L) == out


def test_shortruns():
    L = ['1', '2', '4', '5', '6', '7', '9', '10', '12', '78', '79', '80']
    out = "1, 2, 4–7, 9, 10, 12, 78–80"
    assert format_int_list_with_runs(L) == out
