# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2021-2022 Andrew Rechnitzer
# Copyright (C) 2021-2023 Colin B. Macdonald

from collections import defaultdict
from datetime import datetime, timezone
import json
import logging

from plom.comment_utils import generate_new_comment_ID
from plom.misc_utils import datetime_to_json
from plom.db.tables import Rubric, User, Test, QGroup


log = logging.getLogger("DB")

# ------------------
# Rubric stuff (prefix still M since is marker-stuff)


def McreateRubric(self, user_name, rubric):
    """Create a new rubric entry in the DB

    Args:
        user_name (str): name of user creating the rubric element
        rubric (dict): dict containing the rubric details.
            Must contain these fields:
            `{kind: "relative", display_delta: "-1", value: -1, out_of: 0, text: "blah", question: 2}`
            # TODO: make out_of optional for relative rubrics?
            `{kind: "absolute", display_delta: "1 / 5", value: 1, out_of: 5, text: "blah", question: 2}`
            The following fields are optional and empty strings will be
            substituted:
            `{tags: "blah", meta: "blah", versions: [1, 2], parameters: []}`
            Currently, its ok if it contains other fields: they are
            ignored.
            ``versions`` should be a list of integers, or the empty list
            which means "all versions".
            ``parameters`` is list of per-version substitutions.

    Returns:
        tuple: `(True, key)` or `(False, err_msg)` where `key` is the
        key for the new rubric.  Can fail if missing fields.
    """
    need_fields = ("kind", "display_delta", "value", "out_of", "text", "question")
    optional_fields_and_defaults = (
        ("tags", ""),
        ("meta", ""),
        ("versions", []),
        ("parameters", []),
    )
    if any(x not in rubric for x in need_fields):
        return (False, "Must have all fields {}".format(need_fields))
    for f, d in optional_fields_and_defaults:
        if f not in rubric:
            rubric = rubric.copy()  # in case caller uses reference
            rubric[f] = d
    uref = User.get(name=user_name)  # authenticated, so not-None
    with self._db.atomic():
        # build unique key while holding atomic access
        key = generate_new_comment_ID()
        while Rubric.get_or_none(key=key) is not None:
            key = generate_new_comment_ID()
        Rubric.create(
            key=key,
            user=uref,
            question=rubric["question"],
            kind=rubric["kind"],
            display_delta=rubric["display_delta"],
            value=rubric["value"],
            out_of=rubric["out_of"],
            text=rubric["text"],
            versions=json.dumps(rubric["versions"]),
            parameters=json.dumps(rubric["parameters"]),
            creationTime=datetime.now(timezone.utc),
            modificationTime=datetime.now(timezone.utc),
            meta=rubric["meta"],
            tags=rubric["tags"],
        )
    return (True, key)


def MgetRubrics(self, question=None):
    """Get list of rubrics sorted by kind, then delta, then text."""
    rubric_list = []
    if question is None:
        query = Rubric.select().order_by(Rubric.kind, Rubric.display_delta, Rubric.text)
    else:
        query = (
            Rubric.select()
            .where(Rubric.question == question)
            .order_by(Rubric.kind, Rubric.display_delta, Rubric.text)
        )
    for r in query:
        rubric_list.append(
            {
                "id": r.key,
                "kind": r.kind,
                "display_delta": r.display_delta,
                "value": r.value,
                "out_of": r.out_of,
                "text": r.text,
                "tags": r.tags,
                "question": r.question,
                "versions": json.loads(r.versions),
                "parameters": json.loads(r.parameters),
                "meta": r.meta,
                "count": r.count,
                "username": r.user.name,
                "created": datetime_to_json(r.creationTime),
                "modified": datetime_to_json(r.modificationTime),
            }
        )
    return rubric_list


def MmodifyRubric(self, user_name, key, change):
    """Modify or create a rubric based on an existing rubric in the DB.

    Currently this modifies the existing rubric, increasing its revision
    number.  However, this is subject to change and should be considered
    an implementation detail.  Its very likely we will move to an
    immutable model.  At any rate, the returned `new_key` should be
    considered as replacing the original and the old key should not be
    used to place new annotations.  It might however be used to find
    outdated ones to tag or otherwise update papers.

    Args:
        user_name (str): name of user creating the rubric element
        key(str): key for the rubric
        change (dict): dict containing the changes to make to the
            rubric.  Must contain these fields:
            `{kind: "relative", delta: "-1", text: "blah", tags: "blah", meta: "blah"}`
            Other fields will be ignored.  Note this means you can think
            you are changing, e.g., the question but this will silently
            not happen.
            TODO: in the future we might prevent changing the "kind"
            or the sign of the delta.

    Returns:
        tuple: `(True, new_key)` containing the newly generated key
        (which might be the old key but this is not promised),
        or `(False, "incomplete")`, or `(False, "noSuchRubric")`.
    """
    need_fields = ("display_delta", "text", "tags", "meta", "kind", "value", "out_of")
    if any(x not in change for x in need_fields):
        return (False, "incomplete")
    uref = User.get(name=user_name)  # authenticated, so not-None
    # check if the rubric exists made by this user - cannot modify other user's rubric
    # TODO: should we have another bail case here `(False, "notYours")`?
    # TODO: maybe manager will be able modify all rubrics.
    rref = Rubric.get_or_none(key=key, user=uref)
    if rref is None:
        return (False, "noSuchRubric")

    with self._db.atomic():
        rref.kind = change["kind"]
        rref.display_delta = change["display_delta"]
        rref.value = change["value"]
        rref.out_of = change["out_of"]
        rref.text = change["text"]
        rref.versions = json.dumps(change["versions"])
        rref.parameters = json.dumps(change["parameters"])
        rref.modificationTime = datetime.now(timezone.utc)
        rref.revision += 1
        rref.meta = change["meta"]
        rref.tags = change["tags"]
        rref.save()
    return (True, key)


def Rget_tests_using_given_rubric(self, key):
    """Given the rubric, return counts of the the number of times it is used in tests."""
    rref = Rubric.get_or_none(key=key)
    test_dict = defaultdict(int)
    if rref is None:
        return (False, "noSuchRubric")
    for arlink_ref in rref.arlinks:
        aref = arlink_ref.annotation
        # skip any outdated annotations
        if aref.outdated is True:
            continue
        # otherwise append this test number.
        test_dict[aref.qgroup.test.test_number] += 1
    return (True, test_dict)


def Rget_rubrics_in_a_given_test(self, test_number):
    """Return counts of number of times rubrics used in latest annotations of a given test (indep of question/version)"""

    tref = Test.get_or_none(test_number=test_number)
    if tref is None:
        return (False, "noSuchTest")
    rubric_dict = defaultdict(int)
    for qref in tref.qgroups:
        aref = qref.annotations[-1]
        # skip if this annotation is outdated - this should not happen
        if aref.outdated is True:
            continue
        for arlink_ref in aref.arlinks:
            rubric_dict[arlink_ref.rubric.key] += 1
    return (True, rubric_dict)


def Rget_test_rubric_count_matrix(self):
    """Return count matrix of rubric vs test_number"""
    adjacency = defaultdict(list)
    for tref in Test.select():
        tn = tref.test_number
        for qref in tref.qgroups:
            aref = qref.annotations[-1]
            if aref.outdated is True:  # this should not happen
                continue
            for arlink_ref in aref.arlinks:
                adjacency[tn].append(arlink_ref.rubric.key)
    return adjacency


def Rget_rubric_counts(self):
    """Return dict of rubrics indexed by key containing min details and counts"""
    rubric_info = {}
    # note that the rubric-count in the rubric table is total number
    # used in all annotations not just the latest annotation
    # so we recompute the counts now.

    # Go through rubrics adding them to the above with count=0
    # and minimal info.
    for rref in Rubric.select():
        rubric_info[rref.key] = {
            "id": rref.key,
            "kind": rref.kind,
            "display_delta": rref.display_delta,
            "value": rref.value,
            "out_of": rref.out_of,
            "text": rref.text,
            "count": 0,
            "username": rref.user.name,
            "question": rref.question,
            "versions": str(json.loads(rref.versions)).strip("[]"),  # e.g., "1, 2, 3"
            "parameters": str(json.loads(rref.versions)),
        }
        # TODO: Issue #2406: can versions just be the list of ints?
        # TODO: need to look who calls this: feel like it might end up as
        # the column header of a spreadsheet.

    # now go through all rubrics that **have** been used
    # and increment the count
    for qref in QGroup.select().where(QGroup.marked == True):  # noqa: E712
        # grab latest annotation for each qgroup.
        aref = qref.annotations[-1]
        # skip if this annotation is outdated - this should not happen
        if aref.outdated is True:
            continue
        # go through the rubric links
        for arlink_ref in aref.arlinks:
            rref = arlink_ref.rubric
            rubric_info[rref.key]["count"] += 1

    return rubric_info


def Rget_rubric_details(self, key):
    """Get a given rubric by its key, return its details and all the tests using that rubric."""
    r = Rubric.get_or_none(Rubric.key == key)
    if r is None:
        return (False, "No such rubric.")
    rubric_details = {
        "id": r.key,
        "kind": r.kind,
        "display_delta": r.display_delta,
        "value": r.value,
        "out_of": r.out_of,
        "text": r.text,
        "tags": r.tags,
        "question": r.question,
        "versions": json.loads(r.versions),
        "parameters": json.loads(r.parameters),
        "meta": r.meta,
        "count": r.count,
        "username": r.user.name,
        "created": datetime_to_json(r.creationTime),
        "modified": datetime_to_json(r.modificationTime),
        "test_list": [],
    }
    # now compute all tests using that rubric.
    # find all the annotations
    import logging

    for arlink_ref in r.arlinks:
        logging.warn(f"Looking at arlink = {arlink_ref}")
        aref = arlink_ref.annotation
        logging.warn(f"Looking at aref = {aref}")
        # check if that annotation is the latest
        if aref.outdated is True:
            continue
        # else append it.
        rubric_details["test_list"].append(aref.qgroup.test.test_number)
    # recompute the count since the original actually counts how many
    # annotations (current or not) it is used in - is an overcount.
    rubric_details["count"] = len(rubric_details["test_list"])
    return (True, rubric_details)
