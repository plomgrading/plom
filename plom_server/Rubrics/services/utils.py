# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2023 Brennen Chiu
# Copyright (C) 2019-2025 Colin B. Macdonald
# Copyright (C) 2019-2025 Andrew Rechnitzer
# Copyright (C) 2020 Dryden Wiebe
# Copyright (C) 2021 Nicholas J H Lai
# Copyright (C) 2023 Julian Lapenna
# Copyright (C) 2023 Divy Patel
# Copyright (C) 2023 Natalie Balashov
# Copyright (C) 2024-2025 Aden Chan
# Copyright (C) 2024 Bryan Tanady
# Copyright (C) 2024 Aidan Murphy

import math
from typing import Any

from ..models import Rubric


_frac_value_tolerance = 1e-7


def _Rubric_to_dict(r: Rubric) -> dict[str, Any]:
    return {
        "rid": r.rid,
        "kind": r.kind,
        "display_delta": r.display_delta,
        "value": r.value,
        "out_of": r.out_of,
        "text": r.text,
        "tags": r.tags,
        "meta": r.meta,
        "username": r.user.username,
        "question_index": r.question_index,
        "versions": r.versions,
        "parameters": r.parameters,
        "system_rubric": r.system_rubric,
        "published": r.published,
        "last_modified": r.last_modified,
        "modified_by_username": (
            None if not r.modified_by_user else r.modified_by_user.username
        ),
        "revision": r.revision,
        "subrevision": r.subrevision,
        "pedagogy_tags": [tag.tag_name for tag in r.pedagogy_tags.all()],
    }


def _list_of_rubrics_to_dict_of_dict(rlist: list[Rubric]) -> dict[int, dict[str, Any]]:
    """Return dict of rubrics as dict with rid as key."""
    # don't track usernames - reduce DB calls.
    return {
        r.rid: {
            "rid": r.rid,
            "kind": r.kind,
            "display_delta": r.display_delta,
            "value": r.value,
            "out_of": r.out_of,
            "text": r.text,
            "tags": r.tags,
            "meta": r.meta,
            "question_index": r.question_index,
            "versions": r.versions,
            "parameters": r.parameters,
            "system_rubric": r.system_rubric,
            "published": r.published,
            "last_modified": r.last_modified,
            "revision": r.revision,
            "subrevision": r.subrevision,
            "latest": r.latest,
        }
        for r in rlist
    }


# There are no single unicode chars for 3/10, 7/10, 9/10 but we can use multichar
# strings which seem to render nicely both in web and Qt client (on GNU/Linux).
# TODO: test on Windows/macOS: could instead fallback to ASCII "3/10".
_fraction_table = (
    (1 / 2, "\N{VULGAR FRACTION ONE HALF}"),
    (1 / 4, "\N{VULGAR FRACTION ONE QUARTER}"),
    (3 / 4, "\N{VULGAR FRACTION THREE QUARTERS}"),
    (1 / 3, "\N{VULGAR FRACTION ONE THIRD}"),
    (2 / 3, "\N{VULGAR FRACTION TWO THIRDS}"),
    (1 / 5, "\N{VULGAR FRACTION ONE FIFTH}"),
    (2 / 5, "\N{VULGAR FRACTION TWO FIFTHS}"),
    (3 / 5, "\N{VULGAR FRACTION THREE FIFTHS}"),
    (4 / 5, "\N{VULGAR FRACTION FOUR FIFTHS}"),
    (1 / 8, "\N{VULGAR FRACTION ONE EIGHTH}"),
    (3 / 8, "\N{VULGAR FRACTION THREE EIGHTHS}"),
    (5 / 8, "\N{VULGAR FRACTION FIVE EIGHTHS}"),
    (7 / 8, "\N{VULGAR FRACTION SEVEN EIGHTHS}"),
    (1 / 10, "\N{VULGAR FRACTION ONE TENTH}"),
    (
        3 / 10,
        "\N{SUPERSCRIPT THREE}\N{FRACTION SLASH}\N{SUBSCRIPT ONE}\N{SUBSCRIPT ZERO}",
    ),
    (
        7 / 10,
        "\N{SUPERSCRIPT SEVEN}\N{FRACTION SLASH}\N{SUBSCRIPT ONE}\N{SUBSCRIPT ZERO}",
    ),
    (
        9 / 10,
        "\N{SUPERSCRIPT NINE}\N{FRACTION SLASH}\N{SUBSCRIPT ONE}\N{SUBSCRIPT ZERO}",
    ),
)


def fractional_part_is_nth(
    value: int | float,
    N: int,
) -> bool:
    """Is the non-zero fractional part an Nth?

    For example, when N is 3, we return True on 4.3333333, 1.6666667,
    or -1.3333333 but False for 0.333 or 1.25:
    >>> fractional_part_is_nth(4.33333333, 3)
    True

    >>> fractional_part_is_nth(1.66666667, 3)
    True

    >>> fractional_part_is_nth(-1.33333333, 3)
    True

    >>> fractional_part_is_nth(0.333, 3)
    False

    >>> fractional_part_is_nth(0.25, 3)
    False

    >>> fractional_part_is_nth(0.25, 4)
    True
    """
    # delegate to a different function which returns a "pinned value"
    # when an Nth is detected, or None if not.   The "pinned value" is
    # more accurate but we only return a bool.
    pinned_value = pin_to_fractional_nth(value, N)
    if pinned_value is None:
        return False
    return True


def pin_to_fractional_nth(
    value: int | float,
    N: int,
) -> float | None:
    """Replace the value with a nearby fraction of Nth.

    For example, when N is 3, we return more accurate values for
    4.3333333, 1.6666667, or -1.3333333, but None for 0.333 or 1.25:
    >>> pin_to_fractional_nth(4.3333333, 3)
    4.333333333333333

    >>> pin_to_fractional_nth(1.6666667, 3)
    1.6666666666666665

    >>> pin_to_fractional_nth(-1.3333333, 3)
    -1.3333333333333333

    >>> pin_to_fractional_nth(0.333, 3)

    >>> pin_to_fractional_nth(1.25, 3)

    >>> pin_to_fractional_nth(1.25, 4)
    1.25

    TODO: maybe we need a `tuple(bool, float | None)` return?
    """
    tol = _frac_value_tolerance

    if value < 0:
        local_value = -value
    else:
        local_value = value

    int_part = math.trunc(local_value)
    frac_part = local_value - int_part
    for frac in (float(x) / N for x in range(1, N)):
        if frac - tol < frac_part < frac + tol:
            if value < 0:
                return -(int_part + frac)
            else:
                return int_part + frac
    return None


def _generate_display_delta(
    value: int | float | str,
    kind: str,
    out_of: int | float | str | None = None,
) -> str:
    """Generate the display delta for a rubric.

    Args:
        value: the value of the rubric.
        kind: the kind of the rubric.
        out_of: the maximum value of the rubric, required for
            absolute rubrics, none for other rubrics

    Returns:
        The display delta as a string, which may include unicode
        symbols for fractions.  When ``kinda`` is "neutral", the
        reply will always be ``"."``, although this could change
        in the future.

    Raises:
        ValueError: if the kind is not valid.
        ValueError: if the kind is absolute and out_of is not provided.

    Note that certain fractions with small integer denominators will be
    rendered as fractions.  Currently the detection of such relies on
    a small internal tolerance of roughly sqrt machine epsilon.  This
    means for example that `0.66666667` will convert into the fraction
    two thirds.
    """
    value = float(value) if isinstance(value, str) else value
    out_of = float(out_of) if isinstance(out_of, str) else out_of

    tol = _frac_value_tolerance

    if kind == "absolute":
        if out_of is None:
            raise ValueError("out_of is required for absolute rubrics.")
        value_str = None
        if isinstance(value, int) or value.is_integer():
            value_str = f"{value:g}"
        for frac, frac_str in _fraction_table:
            if frac - tol < value < frac + tol:
                value_str = frac_str
        if value_str is None:
            value_str = f"{value}"

        out_of_str = None
        if isinstance(out_of, int) or out_of.is_integer():
            out_of_str = f"{out_of:g}"
        for frac, frac_str in _fraction_table:
            if frac - tol < out_of < frac + tol:
                out_of_str = frac_str
        if out_of_str is None:
            out_of_str = f"{out_of}"

        return f"{value_str} of {out_of_str}"
    elif kind == "relative":
        for frac, frac_str in _fraction_table:
            if frac - tol < value < frac + tol:
                return f"+{frac_str}"
            if -frac - tol < value < -frac + tol:
                return f"-{frac_str}"
        if value > 0:
            return f"+{value:g}"
        else:
            # Negative sign applied automatically
            return f"{value:g}"
    elif kind == "neutral":
        return "."
    else:
        raise ValueError(f"Invalid kind: {kind}.")
