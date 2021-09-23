# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2021 Colin B. Macdonald

import sys

if sys.version_info >= (3, 7):
    import importlib.resources as resources
else:
    import importlib_resources as resources

import toml

from plom.produce import get_messenger


def upload_rubrics(msgr, rubrics):
    """Upload a list of rubrics to a server."""
    for rub in rubrics:
        # TODO: some autogen ones are also made by manager?
        if rub.get("username", None) == "HAL":
            continue
        # TODO: ask @arechnitzer about this question_number discrepancy
        rub["question"] = rub["question_number"]
        msgr.McreateRubric(rub)


def upload_demo_rubrics(msgr, numquestions=3):
    """Load some demo rubrics and upload to server.

    Args:
        msgr (Messenger/tuple): a connected Messenger object or a tuple
            of `(str, str)` for server/password.

    TODO: get number of questions from the server spec.

    The demo data is a bit sparse: we fill in missing pieces and
    multiply over questions.
    """
    try:
        server, password = msgr
    except TypeError:
        return _upload_demo_rubrics(msgr, numquestions)

    msgr = get_messenger(server, password)
    try:
        return _upload_demo_rubrics(msgr, numquestions)
    finally:
        msgr.closeUser()
        msgr.stop()


def _upload_demo_rubrics(msgr, numquestions=3):
    """Load some demo rubrics and upload to server.

    Args:
        msgr (Messenger): a connected Messenger object.

    The demo data is a bit sparse: we fill in missing pieces and
    multiply over questions.
    """
    rubrics_in = toml.loads(resources.read_text("plom", "demo_rubrics.toml"))
    rubrics_in = rubrics_in["rubric"]
    rubrics = []
    for rub in rubrics_in:
        if not hasattr(rub, "kind"):
            if rub["delta"] == ".":
                rub["kind"] = "neutral"
            elif rub["delta"].startswith("+") or rub["delta"].startswith("-"):
                rub["kind"] = "relative"
            else:
                raise ValueError(f'not sure how to map "kind" for rubric:\n  {rub}')
        # Multiply rubrics w/o question numbers, avoids repetition in demo file
        if not hasattr(rub, "question_number"):
            for q in range(1, numquestions + 1):
                r = rub.copy()
                r["question_number"] = q
                rubrics.append(r)
        else:
            rubrics.append(rub)
    upload_rubrics(msgr, rubrics)
    return len(rubrics)
