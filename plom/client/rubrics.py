# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2024 Colin B. Macdonald

from __future__ import annotations

import html
from typing import Any

import arrow

from plom.plom_exceptions import PlomInconsistentRubric, PlomInvalidRubric


def compute_score_naive(rubrics: list[dict[str, Any]], maxscore: int) -> int:
    """Compute score given a set of rubrics, using naive straight sum rules.

    Args:
        rubrics: list of rubrics.
        maxscore: the maximum anticipated score

    Returns:
        The computed score

    Raises:
        ValueError: score is outside range [0, maxscore].

    This is probably the simplest scoring system: literally
    just add/subject the values of each rubric.  Likely too
    simple for actual use.
    """
    score = 0
    for r in rubrics:
        if r["kind"] != "neutral":
            # neutral should have value 0, but doesn't hurt
            score += int(r["value"])
    if score < 0 or score > maxscore:
        raise ValueError("score is out of range")
    return score


def compute_score_legacy2022(
    rubrics: list[dict[str, Any]], maxscore: int
) -> int | None:
    """Compute score given a set of rubrics, using "Plom 2022" rules.

    Args:
        rubrics (list): each rubric is dict with (at least) these
            keys: `kind`, `value`.  Kind must be a string in
            ``("absolute", "relative", "neutral")``.
        maxscore (int): the maximum anticipated score

    Returns:
        None/int: the computed score or `None` if there are no mark-changing
        annotations on the page.  Note `None` is different from `0`.

    Raises:
        PlomInconsistentRubric: for example, absolute and relative rubrics
            cannot be mixed.
        ValueError: int is outside range [0, maxscore], or non-zero,
            non-full marks absolute rubrics in use.
        PlomInvalidRubric: unexpectedly invalid rubric.

    Tries to follow the rules as used in 2022, as closely as possible.
    """
    score = None

    for r in rubrics:
        if r["kind"] not in ("absolute", "relative", "neutral"):
            raise PlomInvalidRubric(f'Invalid rubric kind={r["kind"]}')

    absolutes = [r for r in rubrics if r["kind"] == "absolute"]
    if len(absolutes) > 1:
        raise PlomInconsistentRubric("Can use at most one absolute rubric")

    for r in absolutes:
        if int(r["value"]) not in (0, maxscore):
            raise ValueError("legacy2022 allows only 0 or full-mark absolute rubrics")
        if score is None:
            score = 0
        score += int(r["value"])

    # next, decide if up or down (not both) and adjust
    uppers = [
        int(r["value"])
        for r in rubrics
        if r["kind"] == "relative" and int(r["value"]) > 0
    ]
    downrs = [
        int(r["value"])
        for r in rubrics
        if r["kind"] == "relative" and int(r["value"]) < 0
    ]

    if uppers and downrs:
        raise PlomInconsistentRubric("Cannot mix up and down deltas")
    if len(absolutes) > 0 and (uppers or downrs):
        raise PlomInconsistentRubric("Cannot relative and absolute rubrics")

    if uppers:
        score = sum(uppers)
    if downrs:
        score = maxscore + sum(downrs)

    if score is not None and (score < 0 or score > maxscore):
        raise ValueError("score is out of range")
    return score


def compute_score_locabs(rubrics: list[dict[str, Any]], maxscore: int) -> int | None:
    """Compute score given a set of rubrics.

    A new set of rubric summation rules, designed to allow mixing up
    "locally absolute" rubrics for per-part marking, combined with
    +/- rubrics when they are unambiguous.

    Args:
        rubrics (list): each rubric is dict with (at least) these
            keys: `kind`, `value`.  Kind must be a string in
            ``("absolute", "relative", "neutral")``.
            Any ``kind="absolute"`` must also have `out_of` fields.
        maxscore (int): the maximum anticipated score

    Returns:
        None/int: the computed score or `None` if there are no mark-changing
        annotations on the page.  Note `None` is different from `0`.

    Raises:
        PlomInconsistentRubric: for example, absolute and relative rubrics
            cannot be mixed.
        ValueError: int is outside range [0, maxscore], or absolute rubrics
            are out of their own range ``[0, out_of]``.  Can also be because
            the total of all ``out_of`` are more than maxscore.  The absolute
            rubrics give upper/lower bounds for possible scores which raise
            ValueErrors if exceeded by relative rubrics.  More than one
            rubric from an exclusive group is a ValueError.
        PlomInvalidRubric: unexpectedly invalid rubric.
    """
    lo_score = 0
    hi_score = maxscore
    sum_out_of = 0

    for r in rubrics:
        if r["kind"] not in ("absolute", "relative", "neutral"):
            raise PlomInvalidRubric(f'Invalid rubric kind={r["kind"]}')

    # first ensure at most one member of an exclusive group
    exclusives = []
    for r in rubrics:
        try:
            # TODO: assumes no spaces in tags
            tt = r["tags"].split()
        except KeyError:
            continue
        for t in tt:
            if t.startswith("exclusive:"):
                # TODO: Python >= 3.9
                # g = t.removeprefix("exclusive:")
                g = t[len("exclusive:") :]
                if g in exclusives:
                    raise ValueError(f'more than one from exclusive group "{g}"')
                exclusives.append(g)

    # step one: add up all the absolute rubrics
    absolutes = [r for r in rubrics if r["kind"] == "absolute"]

    for r in absolutes:
        out_of = r["out_of"]
        if out_of not in range(1, maxscore + 1):
            # TODO: or Inconsistent?
            raise ValueError(f"out_of is outside of [1, {maxscore}]")
        if r["value"] not in range(0, out_of + 1):
            # TODO: or Inconsistent?
            raise ValueError(f"value is outside of [0, out_of] where out_of={out_of}")
        lo_score += r["value"]
        hi_score -= r["out_of"] - r["value"]
        sum_out_of += out_of

    if sum_out_of > maxscore:
        # TODO: or Inconsistent?
        raise ValueError(f"sum of out_of is outside [0, {maxscore}]")

    uppers = [r for r in rubrics if r["kind"] == "relative" and r["value"] > 0]
    downrs = [r for r in rubrics if r["kind"] == "relative" and r["value"] < 0]

    # we now have a bracket [lo_score, hi_score]
    # e.g., suppose question out of 10 and two abs rubrics used
    # 3/4, 2/4 -> [5, 7]
    # Now relative "+1" rubrics modify the 5.  Relative "-1" rubrics
    # modify the 7.
    #
    # But you cannot lift the 5 above 7 nor drop the 7 below 5.

    # TODO: if bracket from abs is trivial, then further relatives are
    # modifiers.  In this case, we could decide mixing +/- is unambiguous.

    # step two: adjust with relative rubrics
    # uppers add to lower bound
    # downers subtract from the upper bound
    if uppers and downrs:
        # TODO: might relax above
        # e.g., if nontrivial bracket than its ambiguous to mix +/-
        raise PlomInconsistentRubric("Ambiguous to mix up and down deltas")

    if not absolutes and not uppers and not downrs:
        return None

    score = lo_score
    if uppers:
        score = lo_score + sum(r["value"] for r in uppers)
    if downrs:
        score = hi_score + sum(r["value"] for r in downrs)

    if score < 0 or score > maxscore:
        raise ValueError("score is out of range")

    if score < lo_score:
        raise ValueError("cannot drop score below that established by absolute rubrics")
    if score > hi_score:
        raise ValueError("cannot lift score above that established by absolute rubrics")

    return score


# compute_score = compute_score_naive
# compute_score = compute_score_legacy2022
compute_score = compute_score_locabs


def render_rubric_as_html(r: dict[str, Any]) -> str:
    display_delta = html.escape(r["display_delta"])
    text = html.escape(r["text"])

    # Sadly Qt does not seem to understand borders on spans.
    # This seems a little plain:
    # return f"""
    #    <span style="color:#FF0000;"><b>{display_delta}</b> {r["text"]}</span>
    # """

    return f"""
        <table style="color:#FF0000;">
          <tr>
            <td style="padding:2px; border-width:1px; border-style:solid; border-color:#FF0000;">
              <b>{display_delta}</b>
            </td>
            <td style="padding:2px; border-width:1px; border-style:dotted; border-color:#FF0000; border-left-style:None;">
             {text}
            </td>
          </tr>
        </table>
    """


def _diff_line(a: str, b: str) -> str:
    a = html.escape(a)
    b = html.escape(b)
    lines = []
    if a:
        lines.append(f'<span style="color:#AA0000;"><b>-</b> {a}</span>')
    if b:
        lines.append(f'<span style="color:#00AA00;"><b>+</b> {b}</span>')
    return f"""
      <tt>
        {"<br />".join(lines)}
      </tt>
    """


def _diff_compact(a: str, b: str, *, label: str = "") -> str:
    a = html.escape(a)
    b = html.escape(b)
    return f"""
      <tt>&nbsp; </tt>{label} <span style="color:#AA0000;">{a}</span>
      &rarr;
      <span style="color:#00AA00;">{b}</span>
    """


def _context(a: str) -> str:
    a = html.escape(a)
    return f"""
      <tt>
        <span style="color:#777777;">&nbsp; {a}</span>
      </tt>
    """


def diff_rubric(p: dict[str, Any], r: dict[str, Any]) -> tuple[bool, str]:
    """Are two rubrics the same, and a marked up visual representation if not.

    Args:
        p: a previous rubric.
        r: the current rubric.  We diff from ``p`` to ``r``.

    Returns:
        tuple: True/False and an string of HTML.  True means they are
        the same and the string is empty in this case.
        Its theoretically possible for two rubrics to be different but
        not visually so.  Its also possible for them to be different
        and still get back False (e.g., differing only in modification
        time).
    """
    rval = True
    mod = r.get("last_modified", "unknown")
    if mod == "unknown":
        # TODO: special support for legacy
        when = mod
    else:
        when = arrow.get(mod).humanize()
    prefix = f'id <tt>{r["id"]}</tt> by {r["username"]} {when}'
    out = ""
    br = "<br />"
    if p["display_delta"] != r["display_delta"]:
        rval = False
        out += br
        out += _diff_compact(p["display_delta"], r["display_delta"])
    else:
        if r["display_delta"] != ".":
            out += _context(r["display_delta"])
    if p["text"] != r["text"]:
        rval = False
        out += br
        out += _diff_line(p["text"], r["text"])
    else:
        out += _context(r["text"])
    if p.get("tags") != r.get("tags"):
        rval = False
        out += br
        out += _diff_line(str(p.get("tags")), str(r.get("tags")))
    if p.get("versions") != r.get("versions"):
        rval = False
        out += br
        out += _diff_compact(
            str(p.get("versions")), str(r.get("versions")), label="versions:"
        )
    if p.get("parameters") != r.get("parameters"):
        rval = False
        out += br
        out += _diff_line(str(p.get("parameters")), str(r.get("parameters")))
    if rval:
        # out = "<i>Not visibly changed</i>"
        out = _context("<no visible changes>")
    return rval, prefix + br + out


def check_for_illadvised(
    rubrics: list[dict[str, Any]], maxscore: int
) -> tuple[bool, str | None, str | None]:
    """Certain combinations of rubrics are legal but not a good idea.

    Args:
        rubrics: the list of rubrics that are currently used on
            this question.
        maxscore: the maximum score for this question.

    Returns:
        If there are no concerns, return tuple `(True, None, None)`.
        Otherwise, ``(False, code, msg)``, where ``code`` is a short
        string for machines and ``msg``
        is some html appropriate to show to the user, e.g., as part of
        a dialog questioning if they really wish to continue.

    Raises:
        KeyError: invalid rubrics.  Rubric must have at least "kind",
            "value", "out_of" keys.  In some cases, also "display_delta"
            and "text" which are used here to render error messages.
    """
    absolutes = [r for r in rubrics if r["kind"] == "absolute"]
    uppers = [r for r in rubrics if r["kind"] == "relative" and r["value"] > 0]
    downrs = [r for r in rubrics if r["kind"] == "relative" and r["value"] < 0]

    if absolutes:
        out_of = sum([r["out_of"] for r in absolutes])
        if out_of != maxscore and not uppers and not downrs:
            msg = f"""
                <p>This question is out of {maxscore}.
                You used {len(absolutes)} absolute rubrics for a
                total &ldquo;out of&rdquo; of {out_of}.</p>
                <p>Are you sure you finished marking this question?</p>
            """
            return False, "out-of-does-not-match-max-mark", msg

    if absolutes and downrs:
        exemplar1 = absolutes[0]
        exemplar2 = downrs[0]
        msg = f"""
            <p>Its probably confusing to combine absolute rubrics such as</p>
            <blockquote>
              {render_rubric_as_html(exemplar1)}
            </blockquote>
            <p>with negative relative rubrics such as</p>
            <blockquote>
              {render_rubric_as_html(exemplar2)}
            </blockquote>
            <p>because the reader may be uncertain what is changed by the
              &ldquo;<b>{exemplar2["display_delta"]}</b>&rdquo;.
            </p>
            <p>Are you sure this feedback will be understandable?</p>
        """
        return False, "confusing-to-mix-abs-minus-relative", msg

    if absolutes and uppers:
        exemplar1 = absolutes[0]
        exemplar2 = uppers[0]
        msg = f"""
            <p>Combining absolute rubrics such as</p>
            <blockquote>
              {render_rubric_as_html(exemplar1)}
            </blockquote>
            <p>with positive relative rubrics such as</p>
            <blockquote>
              {render_rubric_as_html(exemplar2)}
            </blockquote>
            <p>is potentially confusing.</p>
            <p>You may want to <b>check with your team</b>
            to decide if this case is acceptable or not.</p>
        """
        return False, "confusing-to-mix-abs-plus-relative", msg

    return True, None, None
