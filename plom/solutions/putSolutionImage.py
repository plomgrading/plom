# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2021 Andrew Rechnitzer
# Copyright (C) 2021-2022, 2024 Colin B. Macdonald

from __future__ import annotations

from pathlib import Path

from plom.solutions import with_manager_messenger

solution_path = Path("solutionImages")


@with_manager_messenger
def putSolutionImage(
    question: int, version: int, imageName: str | Path, *, msgr
) -> tuple[bool, str]:
    """Push a solution image to a server.

    Args:
        question: which question.
        version: which version.
        imageName: local image name to upload.

    Keyword Args:
        msgr (plom.Messenger/tuple): either a connected Messenger or a
            tuple appropriate for credientials.

    Returns:
        Tuple of `(True, msg)` or `(False, msg)` where `msg` is either an
        error message (on failure) or a diagnostic message (on success).
    """
    spec = msgr.get_spec()
    # nb question,version are strings at this point
    iq = int(question)
    iv = int(version)
    if iq < 1 or iq > spec["numberOfQuestions"]:
        return (False, "Question number out of range")
    if iv < 1 or iv > spec["numberOfVersions"]:
        return (False, "Version number out of range")
    if spec["question"][question]["select"] == "fix" and iv != 1:
        return (False, f"Question{question} has fixed version = 1")

    msgr.putSolutionImage(question, version, imageName)
    return (True, f"Solution for {question}.{version} uploaded")


@with_manager_messenger
def putExtractedSolutionImages(*, msgr):
    """Push all extract solution images to a server.

    This is a more automatic version of :func:`putSolutionImage`:
    instead of just one image, we push all of them for all questions
    and versions.  This means a particular directory structure is
    expected.

    TODO: kwarg for that directory, with default.

    Keyword Args:
        msgr (plom.Messenger/tuple): either a connected Messenger or a
            tuple appropriate for credientials.

    Returns:
        None
    """
    spec = msgr.get_spec()
    # nb question,version are strings at this point
    for q in range(1, spec["numberOfQuestions"] + 1):
        mxv = spec["numberOfVersions"]
        if spec["question"][str(q)]["select"] == "fix":
            mxv = 1  # only do version 1 if 'fix'
        for v in range(1, mxv + 1):
            image_name = solution_path / f"solution.q{q}.v{v}.png"
            msgr.putSolutionImage(q, v, image_name)
