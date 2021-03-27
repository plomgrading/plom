# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2019-2021 Andrew Rechnitzer
# Copyright (C) 2021 Colin B. Macdonald

"""Tools for manipulating version maps."""

import random

# TODO: functions to undo json mucking types up
# TODO: go through and fix all the places with str(q+1)
# TODO: there is some documentation of "param" below that should move elsewhere


def check_version_map(vm, spec=None):
    """Sanity checks on version maps.

    args:
        vm (dict): a dict-of-dicts describing versions.  See the output
            of :func:`plom.finish.make_random_version_map`.
        spec (plom.SpecVerifier/dict): a plom spec or the underlying
            dict, see :func:`plom.SpecVerifier`.

    return:
        None

    raises:
        AssertionError
    """
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
    """Build a random version map.

    args:
        spec (plom.SpecVerifier/dict): A plom exam specificiation or the
            underlying dict.  See :func:`plom.SpecVerifier`.

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
                # there is only one version so all are version 1
                vmap[t][g + 1] = 1
            elif spec["question"][gs]["select"] == "shuffle":
                # version selected randomly in [1, 2, ..., #versions]
                vmap[t][g + 1] = random.randint(1, spec["numberOfVersions"])
            elif spec["question"][gs]["select"] == "param":
                # If caller does not provide a version, all are version 1.
                # Caller can provide a version to group their parameters by any
                # way they wish.  Typically this would be be ease grading, e.g.,
                #   * map negative parameters to v1 and positive to v2.
                #   * map tuples (a,b) with common `b` value to same version.
                # In fact there is no significant difference between `param`
                # and `shuffle` when user data is provided.  But clients or
                # other aspects of the software might behave differently.
                vmap[t][g + 1] = random.randint(1, spec["numberOfVersions"])
    return vmap
