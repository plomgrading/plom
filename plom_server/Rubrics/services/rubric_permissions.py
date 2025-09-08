# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Colin B. Macdonald

import logging
import math
from copy import deepcopy
from typing import Any

from plom_server.Base.services import Settings
from .utils import pin_to_fractional_nth


log = logging.getLogger("RubricService")


# The order of this list is the order shown on screen.  It also
# matters for validity checking: for example we need to check quarter
# before eighth, if the input is 4.25.
# * indent is used to visually indicate which rubrics imply others,
#   it is used with the Bootstrap "ms-n" margin setting.
# * some options imply others.
# TODO: would we ever want to default any of these on?
# Lots of these are supported but currently most are turned off in the UI
# by the `"show-in-ui"` key: change that to True to enable more fractions
_frac_opt_table = [
    {
        "name": "allow-half-point-rubrics",
        "label": "Enable half-point rubrics (such as +\N{VULGAR FRACTION ONE HALF})",
        "denom": 2,
        "readable": "half",  # TODO: presentation_string?
        "implies": [],
        "indent": 0,
        "show-in-ui": True,
    },
    {
        "name": "allow-quarter-point-rubrics",
        "label": "Enable quarter-point rubrics (such as +\N{VULGAR FRACTION ONE QUARTER})",
        "denom": 4,
        "readable": "quarter",
        "implies": ["allow-half-point-rubrics"],
        "indent": 4,
        "show-in-ui": True,
    },
    {
        "name": "allow-eighth-point-rubrics",
        "label": "Enable eighth-point rubrics (such as +\N{VULGAR FRACTION ONE EIGHTH})",
        "denom": 8,
        "readable": "eighth",
        "implies": ["allow-quarter-point-rubrics", "allow-half-point-rubrics"],
        "indent": 5,
        "show-in-ui": False,
    },
    {
        "name": "allow-third-point-rubrics",
        "label": "Enable third-point rubrics (such as +\N{VULGAR FRACTION ONE THIRD})",
        "denom": 3,
        "readable": "third",
        "implies": [],
        "indent": 0,
        "show-in-ui": False,
    },
    {
        "name": "allow-fifth-point-rubrics",
        "label": "Enable fifth-point rubrics (such as +\N{VULGAR FRACTION ONE FIFTH})",
        "denom": 5,
        "readable": "fifth",
        "implies": [],
        "indent": 0,
        "show-in-ui": False,
    },
    {
        "name": "allow-tenth-point-rubrics",
        "label": "Enable tenth-point rubrics (such as +\N{VULGAR FRACTION ONE TENTH})",
        "denom": 10,
        "readable": "tenth",
        "implies": ["allow-fifth-point-rubrics", "allow-half-point-rubrics"],
        "indent": 4,
        "show-in-ui": False,
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
            name = opt["name"]
            assert isinstance(name, str)
            opt["checked"] = (
                True if Settings.key_value_store_get_or_none(name) else False
            )
        rubric_fractional_options = [
            opt
            for opt in rubric_fractional_options
            if opt["show-in-ui"] or opt["checked"]
        ]
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
                Settings.key_value_store_set(a, True)
            else:
                Settings.key_value_store_set(a, False)
        for opt in _frac_opt_table:
            a = str(opt["name"])
            implies = opt["implies"]
            assert isinstance(implies, list)  # help mypy
            if Settings.key_value_store_get_or_none(a):
                for i in implies:
                    Settings.key_value_store_set(i, True)

    @staticmethod
    def pin_to_allowed_fraction(v: float | int | str) -> float:
        """Adjust the value if its close enough to a fraction, or raise an exception depending on settings.

        Returns:
            A floating point number close to the input, provided the input was
            close enough to an allowed value (an integer or a fraction).

        Raises:
            ValueError: that value isn't supported or is currently disallowed.
        """
        v = float(v)
        f = v - math.trunc(v)
        if not f:
            # zero fractional part, nothing to do here
            return v

        for opt in _frac_opt_table:
            name = opt["name"]
            assert isinstance(name, str)
            N = opt["denom"]
            assert isinstance(N, int)  # help mypy
            readable_denom = opt["readable"]
            vpin = pin_to_fractional_nth(v, N)
            if vpin is None:
                continue
            # TODO: query them all at once for better DB access?
            if not Settings.key_value_store_get_or_none(name):
                raise ValueError(
                    f"{readable_denom}-point rubrics are currently not allowed"
                )
            return vpin
        # got all the way through the table, and it wasn't allowed
        raise ValueError(f"Score {v} with fractional part {f} are not supported")
