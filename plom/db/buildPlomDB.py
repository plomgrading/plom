# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2019-2021 Andrew Rechnitzer
# Copyright (C) 2019-2023 Colin B. Macdonald
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
    log.info("Building special manager-generated rubrics")
    # create standard manager delta-rubrics - but no 0, nor +/- max-mark
    for q in range(1, 1 + spec["numberOfQuestions"]):
        mx = spec["question"]["{}".format(q)]["mark"]
        # make zero mark and full mark rubrics
        # Note: the precise "no answer given" string is repated in db_create.py
        rubric = {
            "kind": "absolute",
            "display_delta": f"0 of {mx}",
            "value": "0",
            "out_of": mx,
            "text": "no answer given",
            "question": q,
            "meta": "Is this answer blank or nearly blank?  Please do not use "
            + "if there is any possibility of relevant writing on the page.",
        }
        ok, key_or_err = db.McreateRubric("manager", rubric)
        if not ok:
            raise ValueError(f"Failed to build no-answer-rubric Q{q}: {key_or_err}")
        log.info("Built no-answer-rubric Q%s: key %s", q, key_or_err)

        rubric = {
            "kind": "absolute",
            "display_delta": f"0 of {mx}",
            "value": "0",
            "out_of": mx,
            "text": "no marks",
            "question": q,
            "meta": "There is writing here but its not sufficient for any points.",
        }
        ok, key_or_err = db.McreateRubric("manager", rubric)
        if not ok:
            raise ValueError(f"Failed to build no-marks-rubric Q{q}: {key_or_err}")
        log.info("Built no-marks-rubric Q%s: key %s", q, key_or_err)

        rubric = {
            "kind": "absolute",
            "display_delta": f"{mx} of {mx}",
            "value": f"{mx}",
            "out_of": mx,
            "text": "full marks",
            "question": q,
        }
        ok, key_or_err = db.McreateRubric("manager", rubric)
        if not ok:
            raise ValueError(f"Failed to build full-marks-rubric Q{q}: {key_or_err}")
        log.info("Built full-marks-rubric Q%s: key %s", q, key_or_err)

        # now make delta-rubrics
        for m in range(1, mx + 1):
            # make positive delta
            rubric = {
                "display_delta": "+{}".format(m),
                "value": m,
                "out_of": 0,
                "text": ".",
                "kind": "relative",
                "question": q,
            }
            ok, key_or_err = db.McreateRubric("manager", rubric)
            if not ok:
                raise ValueError(
                    f"Failed to build delta-rubric +{m} for Q{q}: {key_or_err}"
                )
            log.info("Built delta-rubric +%d for Q%s: %s", m, q, key_or_err)
            # make negative delta
            rubric = {
                "display_delta": "-{}".format(m),
                "value": -m,
                "out_of": 0,
                "text": ".",
                "kind": "relative",
                "question": q,
            }
            ok, key_or_err = db.McreateRubric("manager", rubric)
            if not ok:
                raise ValueError(
                    f"Failed to build delta-rubric -{m} for Q{q}: {key_or_err}"
                )
            log.info("Built delta-rubric -%d for Q%s: %s", m, q, key_or_err)


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
