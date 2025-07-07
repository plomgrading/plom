# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Colin B. Macdonald

import logging
from copy import deepcopy
from typing import Any

from plom_server.Base.models import SettingsModel


log = logging.getLogger("RubricService")


# The order of this list is the order shown on screen.
# * indent is used to visually indicate which rubrics imply others,
#   it is used with the Bootstrap "ms-n" margin setting.
# * some options imply others.
# TODO: would we ever want to default any of these on?
_frac_opt_table = [
    {
        "name": "allow-half-point-rubrics",
        "label": "Enable half-point rubrics (such as +\N{VULGAR FRACTION ONE HALF})",
        "indent": 0,
    },
    {
        "name": "allow-quarter-point-rubrics",
        "label": "Enable quarter-point rubrics (such as +\N{VULGAR FRACTION ONE QUARTER})",
        "indent": 4,
        "implies": ["allow-half-point-rubrics"],
    },
    {
        "name": "allow-eighth-point-rubrics",
        "label": "Enable eighth-point rubrics (such as +\N{VULGAR FRACTION ONE EIGHTH})",
        "indent": 5,
        "implies": ["allow-quarter-point-rubrics", "allow-half-point-rubrics"],
    },
    {
        "name": "allow-third-point-rubrics",
        "label": "Enable third-point rubrics (such as +\N{VULGAR FRACTION ONE THIRD})",
        "indent": 0,
    },
    {
        "name": "allow-fifth-point-rubrics",
        "label": "Enable fifth-point rubrics (such as +\N{VULGAR FRACTION ONE FIFTH})",
        "indent": 0,
    },
    {
        "name": "allow-tenth-point-rubrics",
        "label": "Enable tenth-point rubrics (such as +\N{VULGAR FRACTION ONE TENTH})",
        "indent": 4,
        "implies": ["allow-fifth-point-rubrics", "allow-half-point-rubrics"],
    },
]


class RubricPermissionsService:
    """Handles setting/getting and other aspects of Rubric permissions."""

    @staticmethod
    def get_fractional_settings() -> list[dict[str, Any]]:
        rubric_fractional_options = deepcopy(_frac_opt_table)
        # figure out which are currently checked by checking settings
        for opt in rubric_fractional_options:
            opt["checked"] = SettingsModel.cget(opt["name"])
        return rubric_fractional_options

    @staticmethod
    def change_fractional_settings(rp) -> None:
        """Change the settings related to fractional rubrics.

        Args:
            rp: a dict-like, probably `requests.POST`.  It has keys corresponding
                to zero or more of the `allow-X-point-rubrics`.  Their value should
                be the string `"on"`.  Any settings not present will be turned off.
        """
        for opt in _frac_opt_table:
            a = opt["name"]
            if rp.get(a) == "on":
                SettingsModel.cset(a, True)
            else:
                SettingsModel.cset(a, False)
        for opt in _frac_opt_table:
            a = opt["name"]
            implies = opt.get("implies", [])
            if SettingsModel.cget(a):
                for i in implies:
                    SettingsModel.cset(i, True)
