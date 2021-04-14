# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2021 Andrew Rechnitzer
# Copyright (C) 2021 Colin B. Macdonald

from datetime import datetime
import logging

from plom.comment_utils import generate_new_comment_ID
from plom.db.tables import (
    Rubric,
    User,
)
from plom.db.tables import plomdb


log = logging.getLogger("DB")

# ------------------
# Rubric stuff (prefix still M since is marker-stuff)


def McreateRubric(self, user_name, rubric):
    """Create a new rubric entry in the DB

    Args:
        user_name (str): name of user creating the rubric element
        rubric (dict): dict containing the rubric details.
            Must contain these fields:
            `{kind: "relative", delta: "-1", text: "blah", question: 2}`
            The following fields are optional and empty strings will be
            substituted:
            `{tags: "blah", meta: "blah"}`
            Currently, its ok if it contains other fields: they are
            ignored.

    Returns:
        tuple: `(True, key)` or `(False, err_msg)` where `key` is the
            key for the new rubric.  Can fail if missing fields.
    """
    need_fields = ("kind", "delta", "text", "question")
    optional_fields = ("tags", "meta")
    if any(x not in rubric for x in need_fields):
        return (False, "Must have all fields {}".format(need_field))
    for f in optional_fields:
        if f not in rubric:
            rubric = rubric.copy()  # in case caller uses reference
            rubric[f] = ""
    uref = User.get(name=user_name)  # authenticated, so not-None
    with plomdb.atomic():
        # build unique key while holding atomic access
        key = generate_new_comment_ID()
        while Rubric.get_or_none(key=key) is not None:
            key = generate_new_comment_ID()
        Rubric.create(
            key=key,
            user=uref,
            question=rubric["question"],
            kind=rubric["kind"],
            delta=rubric["delta"],
            text=rubric["text"],
            creationTime=datetime.now(),
            modificationTime=datetime.now(),
            meta=rubric["meta"],
            tags=rubric["tags"],
        )
    return (True, key)


def MgetRubrics(self, question_number=None):
    # return the rubric sorted by kind, then delta, then text
    rubric_list = []
    if question_number is None:
        query = Rubric.select().order_by(Rubric.kind, Rubric.delta, Rubric.text)
    else:
        query = (
            Rubric.select()
            .where(Rubric.question == question_number)
            .order_by(Rubric.kind, Rubric.delta, Rubric.text)
        )
    for r in query:
        rubric_list.append(
            {
                "id": r.key,
                "kind": r.kind,
                "delta": r.delta,
                "text": r.text,
                "tags": r.tags,
                "meta": r.meta,
                "count": r.count,
                "created": r.creationTime.strftime("%y:%m:%d-%H:%M:%S"),
                "modified": r.modificationTime.strftime("%y:%m:%d-%H:%M:%S"),
                "username": r.user.name,
                "question_number": r.question,
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
    need_fields = ("delta", "text", "tags", "meta", "kind")
    if any(x not in change for x in need_fields):
        return (False, "incomplete")
    uref = User.get(name=user_name)  # authenticated, so not-None
    # check if the rubric exists made by this user - cannot modify other user's rubric
    # TODO: should we have another bail case here `(False, "notYours")`?
    # TODO: maybe manager will be able modify all rubrics.
    rref = Rubric.get_or_none(key=key, user=uref)
    if rref is None:
        return (False, "noSuchRubric")

    with plomdb.atomic():
        rref.kind = change["kind"]
        rref.delta = change["delta"]
        rref.text = change["text"]
        rref.modificationTime = datetime.now()
        rref.revision += 1
        rref.meta = change["meta"]
        rref.tags = change["tags"]
        rref.save()
    return (True, key)
