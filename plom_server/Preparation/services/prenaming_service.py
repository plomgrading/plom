# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2024 Andrew Rechnitzer
# Copyright (C) 2023-2026 Colin B. Macdonald
# Copyright (C) 2024 Aidan Murphy
# Copyright (C) 2025 Philip D. Loewen

from django.db import transaction

from plom_server.Base.services import Settings
from .preparation_dependency_service import (
    assert_can_modify_prenaming_config,
)


class PrenameSettingService:
    @classmethod
    def get_prenaming_config(cls) -> dict:
        """Get prenaming configuration as a dict."""
        return {
            "xcoord": Settings.key_value_store_get("prenaming_xcoord"),
            "ycoord": Settings.key_value_store_get("prenaming_ycoord"),
        }

    @classmethod
    def set_prenaming_coords(
        cls, xcoord: float | None, ycoord: float | None, *, _check: bool = True
    ) -> None:
        """Set prenaming box position to the given vars.

        Args:
            xcoord: the x-coordinate of the prenaming box to set, or None
                to use a default.
            ycoord: similarly, the y-coordinate.

        Keyword Args:
            _check: usually we assert that we're allowed to do this.  Private
                internal reset stuff can bypass this by passing False.  Don't
                use this.

        Raises:
            PlomDependencyConflict: if the position cannot be modified.
        """
        with transaction.atomic():
            if _check:
                assert_can_modify_prenaming_config()
            if xcoord is None:
                Settings.key_value_store_reset("prenaming_xcoord")
            else:
                Settings.key_value_store_set("prenaming_xcoord", xcoord)
            if ycoord is None:
                Settings.key_value_store_reset("prenaming_ycoord")
            else:
                Settings.key_value_store_set("prenaming_ycoord", ycoord)

    @classmethod
    def reset_prenaming_coords(cls, *, force: bool = False) -> None:
        """Reset prenaming coords to their defaults."""
        cls.set_prenaming_coords(None, None, _check=(not force))
