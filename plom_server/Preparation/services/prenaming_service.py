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
    def get_prenaming_setting(self) -> bool:
        """Get prenaming setting."""
        return Settings.key_value_store_get("prenaming_enabled", False)

    @transaction.atomic
    def set_prenaming_setting(self, enable: bool) -> None:
        """Use the boolean value of the input parameter to set prenaming.

        Raises:
            PlomDependencyConflict: if modification is disallowed.
        """
        assert_can_enable_disable_prenaming()
        Settings.key_value_store_set("prenaming_enabled", enable)

    @classmethod
    def get_prenaming_config(cls) -> dict:
        """Get prenaming configuration as a dict."""
        (default_xcoord, default_ycoord) = cls._default_prenaming_coords()
        return {
            "enabled": cls.get_prenaming_setting(),
            "xcoord": Settings.key_value_store_get("prenaming_xcoord", default_xcoord),
            "ycoord": Settings.key_value_store_get("prenaming_ycoord", default_ycoord),
        }

    @transaction.atomic
    def set_prenaming_coords(self, xcoord: float, ycoord: float) -> None:
        """Set prenaming box position to the given vars.

        Raises:
            PlomDependencyConflict: if the position cannot be modified.
        """
        assert_can_modify_prenaming_config()
        Settings.key_value_store_set("prenaming_xcoord", xcoord)
        Settings.key_value_store_set("prenaming_ycoord", ycoord)

    @staticmethod
    def _default_prenaming_coords() -> tuple[float, float]:
        """The prenaming default coords."""
        return (50, 42)

    def reset_prenaming_coords(self) -> None:
        """Reset prenaming coords to their defaults."""
        xcoord, ycoord = self._default_prenaming_coords()
        self.set_prenaming_coords(xcoord, ycoord)
