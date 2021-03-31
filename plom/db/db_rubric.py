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
            For example
            {delta: "-1", text: "blah", question: "2", tags: "blah", meta: "meta-blah"}

    Returns:
        list: [True, key] - the new key generated
    TODO: Needs some fail-case.
    """

    uref = User.get(name=user_name)  # authenticated, so not-None
    # build a new key for the rubric - must be unique
    key = generate_new_comment_ID()
    while Rubric.get_or_none(key=key) is not None:
        key = generate_new_comment_ID()
    # key is now not present in DB
    with plomdb.atomic():
        Rubric.create(
            key=key,
            user=uref,
            question=rubric["question"],
            delta=rubric["delta"],
            text=rubric["text"],
            creationTime=datetime.now(),
            modificationTime=datetime.now(),
            meta=rubric["meta"],
            tags=rubric["tags"],
        )
    return [True, key]


def MgetRubrics(self, question_number=None):
    rubric_list = []
    if question_number is None:
        query = Rubric.select()
    else:
        query = Rubric.select().where(Rubric.question == question_number)
    for r in query:
        rubric_list.append(
            {
                "id": r.key,
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


def MmodifyRubric(self, user_name, key, rubric):
    """Create a new rubric entry in the DB

    Args:
        user_name (str): name of user creating the rubric element
        key(str): key for the rubric
        rubric (dict): dict containing the rubric details.
            For example
            {delta: "-1", text: "blah", question: "2", tags: "blah", meta: "meta-blah", "key:blahblayh"}

    Returns:
        list: [True, key] - the new key generated, [False, "noSuchRubric"]

    """

    uref = User.get(name=user_name)  # authenticated, so not-None
    # check if the rubric exists made by this user - cannot modify other user's rubric
    rref = Rubric.get_or_none(key=key, user=uref)
    if rref is None:
        return [False, "noSuchRubric"]

    with plomdb.atomic():
        rref.delta = rubric["delta"]
        rref.text = rubric["text"]
        rref.modificationTime = datetime.now()
        rref.revision += 1
        rref.meta = rubric["meta"]
        rref.tags = rubric["tags"]
        rref.save()
    return [True, key]
