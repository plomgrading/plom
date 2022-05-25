# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2019-2021 Andrew Rechnitzer
# Copyright (C) 2021-2022 Colin B. Macdonald

"""Tools for manipulating version maps."""

import random

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
        # Issue #1745: no such restriction and/or not accurate
        assert len(vm) == spec["numberToProduce"]
    rowlens = set()
    for t, qd in vm.items():
        assert isinstance(t, int)
        assert isinstance(qd, dict)
        if spec:
            assert len(qd) == spec["numberOfQuestions"]
        # even if no spec we can ensure all rows the same
        rowlens.add(len(qd))
        for q, v in qd.items():
            assert isinstance(q, int)
            assert isinstance(v, int)
            assert v > 0
            if spec:
                assert v <= spec["numberOfVersions"]
                if spec["question"][str(q)]["select"] == "fix":
                    assert v == 1
    assert len(rowlens) <= 1, "Not all rows had same length"


def make_random_version_map(spec):
    """Build a random version map.

    args:
        spec (plom.SpecVerifier/dict): A plom exam specification or the
            underlying dict.  See :func:`plom.SpecVerifier`.  The most
            important properties are the `numberToProduce`, the
            `numberOfQuestions`, and the `select` of each question.

    return:
        dict: a dict-of-dicts keyed by paper number (int) and then
            question number (int, but indexed from 1 not 0).  Values are
            integers.

    raises:
        KeyError: invalid question selection scheme in spec.
    """
    # we want to have nearly equal numbers of each version - issue #1470
    # first make a list which cycles through versions
    vlist = [(x % spec["numberOfVersions"]) + 1 for x in range(spec["numberToProduce"])]
    # now assign a copy of this for each question, so qvlist[question][testnumber]=version
    qvlist = [
        random.sample(vlist, len(vlist)) for q in range(spec["numberOfQuestions"])
    ]
    # we use the above when a question is shuffled, else we just use v=1.

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
                # the below is purely random, so uneven distribution of versions
                # vmap[t][g + 1] = random.randint(1, spec["numberOfVersions"])
                # replace with more equal distribution of versions from qvlist above
                vmap[t][g + 1] = qvlist[g][t - 1]
                # offset by one due to indices starting from 0

            # TODO: we may enable something like this later
            # elif spec["question"][gs]["select"] == "param":
            #    # If caller does not provide a version, all are version 1.
            #    # Caller can provide a version to group their parameters by any
            #    # way they wish.  Typically this would be be ease grading, e.g.,
            #    #   * map negative parameters to v1 and positive to v2.
            #    #   * map tuples (a,b) with common `b` value to same version.
            #    # In fact there is no significant difference between `param`
            #    # and `shuffle` when user data is provided.  But clients or
            #    # other aspects of the software might behave differently.
            #    vmap[t][g + 1] = random.randint(1, spec["numberOfVersions"])
            else:
                raise KeyError(
                    'Invalid spec: question {} "select" of "{}" is unexpected'.format(
                        gs, spec["question"][gs]["select"]
                    )
                )
    return vmap


def undo_json_packing_of_version_map(vermap_in):
    """JSON must have string keys; undo such to int keys for version map.

    Both the test number and the question number have likely been
    converted to strings by an evil JSON: we build a new dict-of-dicts
    with both converted explicitly to integers.

    Note: sometimes the dict-of-dicts is key'd by page number instead
    of question number.  This same function can be used in that case.
    """
    vmap = {}
    for t, question_vers in vermap_in.items():
        vmap[int(t)] = {int(q): v for q, v in question_vers.items()}
    return vmap
