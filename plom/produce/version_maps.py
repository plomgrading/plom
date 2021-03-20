# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2019-2021 Andrew Rechnitzer
# Copyright (C) 2021 Colin B. Macdonald

"""Tools for manipulating version maps."""

import random

# TODO: functions to undo json mucking types up
# TODO: go through and fix all the places with str(q+1)
# TODO: use this in database building


def check_version_map(vm, spec=None):
    """Sanity checks on version maps."""
    if spec:
        assert len(vm) == spec["numberToProduce"]
    for t, qd in vm.items():
        assert isinstance(t, int)
        assert isinstance(qd, dict)
        if spec:
            assert len(qd) == spec["numberOfQuestions"]
        for q, v in qd.items():
            # TODO: currently str
            # assert isinstance(q, int)
            assert isinstance(v, int)


def make_random_version_map(spec):
    """Rough client-side version map.

    args:
        spec (dict): plom spec as documented elsewhere.  TODO: maybe
            maybe better to pass only the bits we need.

    return:
        dict: a dict-of-dicts keyed by paper number (int) and then
            question number (str, b/c WTF knows).  Values are integers.
    """
    vmap = {}
    for t in range(1, spec["numberToProduce"] + 1):
        vmap[t] = {}
        for g in range(spec["numberOfQuestions"]):  # runs from 0,1,2,...
            gs = str(g + 1)  # now a str and 1,2,3,...
            if spec["question"][gs]["select"] == "fix":
                vmap[t][g + 1] = 1
            elif spec["question"][gs]["select"] == "shuffle":
                vmap[t][g + 1] = random.randint(1, spec["numberOfVersions"])
            elif spec["question"][gs]["select"] == "param":
                vmap[t][g + 1] = random.randint(1, spec["numberOfVersions"])
    return vmap
