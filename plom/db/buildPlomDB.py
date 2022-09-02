# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2019-2021 Andrew Rechnitzer
# Copyright (C) 2019-2022 Colin B. Macdonald
# Copyright (C) 2020 Dryden Wiebe
# Copyright (C) 2021 Nicholas J H Lai

import logging
import random

from plom import check_version_map, make_random_version_map

# from plom.db import PlomDB


log = logging.getLogger("DB")


def buildSpecialRubrics(spec, db):
    """Add special rubrics such as deltas and per-question specific.

    Returns:
        None

    Raises:
        ValueError: if a rubric already exists (likely b/c you've called
            this twice)
    """
    # create no-answer-given rubrics
    for q in range(1, 1 + spec["numberOfQuestions"]):
        if not db.createNoAnswerRubric(q, spec["question"]["{}".format(q)]["mark"]):
            raise ValueError(f"No-answer rubric for q.{q} already exists")
    # create standard manager delta-rubrics - but no 0, nor +/- max-mark
    for q in range(1, 1 + spec["numberOfQuestions"]):
        mx = spec["question"]["{}".format(q)]["mark"]
        # make zero mark and full mark rubrics
        rubric = {
            "kind": "absolute",
            "delta": "0",
            "text": "no marks",
            "question": q,
        }
        if not db.McreateRubric("manager", rubric):
            raise ValueError(f"Manager no-marks-rubric for q.{q} already exists")
        rubric = {
            "kind": "absolute",
            "delta": "{}".format(mx),
            "text": "full marks",
            "question": q,
        }
        if not db.McreateRubric("manager", rubric):
            raise ValueError(f"Manager full-marks-rubric for q.{q} already exists")
        # now make delta-rubrics
        for m in range(1, mx + 1):
            # make positive delta
            rubric = {
                "delta": "+{}".format(m),
                "text": ".",
                "kind": "delta",
                "question": q,
            }
            if not db.McreateRubric("manager", rubric):
                raise ValueError(f"Manager delta-rubric +{m} for q.{q} already exists")
            # make negative delta
            rubric = {
                "delta": "-{}".format(m),
                "text": ".",
                "kind": "delta",
                "question": q,
            }
            if not db.McreateRubric("manager", rubric):
                raise ValueError(f"Manager delta-rubric -{m} for q.{q} already exists")


def initialiseExamDatabaseFromSpec(spec, db, version_map=None):
    """Build metadata for exams from spec but do not build tests in DB.

    Arguments:
        spec (dict): exam specification, see :func:`plom.SpecVerifier`.
        db (database): the database to populate.
        version_map (dict/None): optional predetermined version map
            keyed by test number and question number.  If None, we will
            build our own random version mapping.  For the map format
            see :func:`plom.finish.make_random_version_map`.

    Returns:
        dict: the question-version map.

    Raises:
        ValueError: if database already populated, or attempt to
            build paper n without paper n-1.
        KeyError: invalid question selection scheme in spec.
    """
    if db.is_paper_database_initialised():
        raise ValueError("Database already initialised")

    buildSpecialRubrics(spec, db)
    if not db.createReplacementBundle():
        raise ValueError("Could not create bundle for replacement pages")

    if not version_map:
        # TODO: move reproducible random seed support to the make fcn?
        random.seed(spec["privateSeed"])
        version_map = make_random_version_map(spec)
    check_version_map(version_map)

    return version_map
