# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Colin B. Macdonald

from __future__ import annotations

import html
from typing import Any

import arrow
from PyQt6.QtWidgets import QWidget

from .useful_classes import InfoMsg
from .rubrics import diff_rubric, render_rubric_as_html


class RubricConflictDialog(InfoMsg):
    """Display conflicts between two rubrics.

    Args:
        parent:
        conflict_msg: a string to display explaining the general situation.
            Does not need to be HTML-safe (we will make it so).
        their_rubric: One copy of the rubric, to be labelled "their's".
        our_rubric: another copy of the rubric, to be labelled "our's".
        common_ancestor: The common ancestor of both, we will display
            how each rubric differs from this one.

    Keyword Args:
        ours_right_now: override the "last_modified" time of our_rubric
            to be "now", on by default.

    For now, it just explains the situation but offers no resolution.
    """

    def __init__(
        self,
        parent: QWidget | None,
        conflict_msg: str,
        their_rubric: dict[str, Any],
        our_rubric: dict[str, Any],
        common_ancestor: dict[str, Any],
        *,
        ours_right_now: bool = True,
        **kwargs,
    ):
        same, their_diff = diff_rubric(common_ancestor, their_rubric)
        if ours_right_now:
            # server hasn't seen it to change timestamp, so we'll (temporarily)
            # do it ourselves.
            our_rubric = our_rubric.copy()
            our_rubric["last_modified"] = str(arrow.now())
        same, our_diff = diff_rubric(common_ancestor, our_rubric)
        txt = f"""
            <h3>Rubric change conflict</h3>
            <br />
            <quote>
              <small>
                <tt>{html.escape(conflict_msg)}</tt>
              </small>
            </quote>
            <br />
            <table><tr>
            <td style="padding-right: 2ex; border-right-width: 1px; border-right-style: solid;">
              <h4>Their's</h4>
              {render_rubric_as_html(their_rubric)}
            </td>
            <td style="padding-left: 2ex;">
              <h4>Your's</h4>
              {render_rubric_as_html(our_rubric)}
            </td>
            </tr>
            <tr>
            <td style="padding-right: 2ex; border-right-width: 1px; border-right-style: solid;">
              <b>changes</b><br />
              {their_diff}
            </td>
            <td style="padding-left: 2ex;">
              <b>changes</b><br />
              {our_diff}
            </td>
            </tr></table>
            <p>
              This is work-in-progress,
              for now we always keep &ldquo;Their's&rdquo;.
            </p>
        """
        # "Do you want to keep their's or your's?",
        # TODO: future buttons: [Cancel (and keep theirs)], [further edit theirs], [force submit your's], [edit your's]
        super().__init__(parent, txt, **kwargs)
