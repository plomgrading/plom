# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Colin B. Macdonald

import logging
import math
from copy import deepcopy
from typing import Any

from plom_server.Base.models import SettingsModel
from .utils import fractional_part_is_nth


log = logging.getLogger("RubricService")


# The order of this list is the order shown on screen.  It also
# matters for validity checking: for example we need to check quarter
# before eighth, if the input is 4.25.
# * indent is used to visually indicate which rubrics imply others,
#   it is used with the Bootstrap "ms-n" margin setting.
# * some options imply others.
# TODO: would we ever want to default any of these on?
_frac_opt_table = [
    {
        "name": "allow-half-point-rubrics",
        "label": "Enable half-point rubrics (such as +\N{VULGAR FRACTION ONE HALF})",
        "denom": 2,
        "readable": "half",  # TODO: presentation_string?
        "indent": 0,
    },
    {
        "name": "allow-quarter-point-rubrics",
        "label": "Enable quarter-point rubrics (such as +\N{VULGAR FRACTION ONE QUARTER})",
        "denom": 4,
        "readable": "quarter",
        "implies": ["allow-half-point-rubrics"],
        "indent": 4,
    },
    {
        "name": "allow-eighth-point-rubrics",
        "label": "Enable eighth-point rubrics (such as +\N{VULGAR FRACTION ONE EIGHTH})",
        "denom": 8,
        "readable": "eighth",
        "implies": ["allow-quarter-point-rubrics", "allow-half-point-rubrics"],
        "indent": 5,
    },
    {
        "name": "allow-third-point-rubrics",
        "label": "Enable third-point rubrics (such as +\N{VULGAR FRACTION ONE THIRD})",
        "denom": 3,
        "readable": "third",
        "indent": 0,
    },
    {
        "name": "allow-fifth-point-rubrics",
        "label": "Enable fifth-point rubrics (such as +\N{VULGAR FRACTION ONE FIFTH})",
        "denom": 5,
        "readable": "fifth",
        "indent": 0,
    },
    {
        "name": "allow-tenth-point-rubrics",
        "label": "Enable tenth-point rubrics (such as +\N{VULGAR FRACTION ONE TENTH})",
        "denom": 10,
        "readable": "tenth",
        "implies": ["allow-fifth-point-rubrics", "allow-half-point-rubrics"],
        "indent": 4,
    },
]


class RubricPermissionsService:
    """Handles setting/getting and other aspects of Rubric permissions."""

    @staticmethod
    def get_fractional_settings() -> list[dict[str, Any]]:
        """Get a table of the current fractional rubric settings, suitable for making HTML forms."""
        rubric_fractional_options = deepcopy(_frac_opt_table)
        # figure out which are currently checked by checking settings
        for opt in rubric_fractional_options:
            opt["checked"] = SettingsModel.cget(opt["name"])
        return rubric_fractional_options

    @staticmethod
    def change_fractional_settings(rp: dict[str, str]) -> None:
        """Change the settings related to fractional rubrics.

        Args:
            rp: a dict-like, probably `requests.POST`.  It has keys corresponding
                to zero or more of the `allow-X-point-rubrics`.  Their value should
                be the string `"on"`.  Any settings not present will be turned off.
                Some settings imply others: these will be applied too.
        """
        for opt in _frac_opt_table:
            a = str(opt["name"])
            if rp.get(a) == "on":
                SettingsModel.cset(a, True)
            else:
                SettingsModel.cset(a, False)
        for opt in _frac_opt_table:
            a = str(opt["name"])
            implies = opt.get("implies", [])
            assert isinstance(implies, list)  # help mypy
            if SettingsModel.cget(a):
                for i in implies:
                    SettingsModel.cset(i, True)

    @staticmethod
    def confirm_allowed_fraction(v: float | int) -> None:
        """Against the current settings, if a value isn't a supported fraction raise an exception.

        Raises:
            ValueError: that value isn't supported or is currently disallowed.
        """
        f = v - math.trunc(v)
        if not f:
            # zero fractional part, nothing to do here
            return

        s = SettingsModel.load()
        for opt in _frac_opt_table:
            name = opt["name"]
            N = opt["denom"]
            assert isinstance(N, int)  # help mypy
            readable_denom = opt["readable"]
            if fractional_part_is_nth(v, N):
                # TODO: the detection uses a tolerance but maybe/probably we should
                # round to that tolerance
                if not s.get(name):
                    raise ValueError(
                        f"{readable_denom}-point rubrics are currently not allowed"
                    )
                return
        # got all the way through the table, and it wasn't allowed
        raise ValueError(f"Score {v} with fractional part {f} are not supported")
