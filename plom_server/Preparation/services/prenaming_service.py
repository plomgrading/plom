# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2024 Andrew Rechnitzer
# Copyright (C) 2023-2025 Colin B. Macdonald
# Copyright (C) 2024 Aidan Murphy
# Copyright (C) 2025 Philip D. Loewen

from django.db import transaction

from plom_server.Base.services import Settings
from .preparation_dependency_service import (
    assert_can_enable_disable_prenaming,
    assert_can_modify_prenaming_config,
)


class PrenameSettingService:
    @staticmethod
    def get_prenaming_setting() -> bool:
        """Get prenaming setting."""
        return Settings.key_value_store_get("prenaming_enabled")

    @staticmethod
    def set_prenaming_setting(enable: bool) -> None:
        """Use the boolean value of the input parameter to set prenaming.

        Raises:
            PlomDependencyConflict: if modification is disallowed.
        """
        with transaction.atomic():
            assert_can_enable_disable_prenaming()
            Settings.key_value_store_set("prenaming_enabled", enable)

    @classmethod
    def get_prenaming_config(cls) -> dict:
        """Get prenaming configuration as a dict."""
        return {
            "enabled": Settings.key_value_store_get("prenaming_enabled"),
            "xcoord": Settings.key_value_store_get("prenaming_xcoord"),
            "ycoord": Settings.key_value_store_get("prenaming_ycoord"),
        }

    @classmethod
    def set_prenaming_coords(cls, xcoord: float | None, ycoord: float | None) -> None:
        """Set prenaming box position to the given vars.

        Args:
            xcoord: the x-coordinate of the prenaming box to set, or None
                to use a default.
            ycoord: similarly, the y-coordinate.

        Raises:
            PlomDependencyConflict: if the position cannot be modified.
        """
        with transaction.atomic():
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
    def reset_prenaming_coords(cls) -> None:
        """Reset prenaming coords to their defaults."""
        cls.set_prenaming_coords(None, None)
