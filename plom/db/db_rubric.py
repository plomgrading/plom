from plom.db.tables import *
from datetime import datetime
from plom.comment_utils import generate_new_comment_ID

import logging

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
