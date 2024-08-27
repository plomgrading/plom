# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Colin B. Macdonald
# Copyright (C) 2024 Bryan Tanady

from __future__ import annotations

from PyQt6.QtWidgets import QWidget

from .useful_classes import InfoMsg, WarnMsg


# TODO: more specific link once we have one!
explain = """
    <p>The reasons for this limit may vary but typically you will
    need to meet or communicate with them after reaching the limit,
    before you are able to continue marking additional papers.</p>

    <p>If your instructor has already changed the setting, try
    refreshing your list of marking tasks.</p>

    <p>You can also
    <a href="https://plom.readthedocs.io/en/latest/marking.html#quotas">read
    about Plom&rsquo;s quota settings</a>.</p>
"""


class ExplainQuotaDialog(InfoMsg):
    """A dialog explaining quotas."""

    def __init__(self, parent: QWidget) -> None:
        super().__init__(
            parent,
            "The number of tasks you can mark is currently limited by"
            " your instructor or administrator.",
            info=explain,
            info_pre=False,
        )


class ReachedQuotaLimitDialog(WarnMsg):
    """A dialog for reaching the quota limit with explanations."""

    def __init__(self, parent: QWidget, *, limit: int | None = None) -> None:
        s = "You have reached your task limit"
        if limit is not None:
            s += f" of {limit}"
        s += ".  Please contact your instructor or administrator"
        s += " in order to mark more tasks."
        super().__init__(parent, s, info=explain, info_pre=False)
