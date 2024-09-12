# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2024 Andrew Rechnitzer
# Copyright (C) 2023-2024 Colin B. Macdonald
# Copyright (C) 2024 Aidan Murphy

from django.db import transaction

from ..models import PrenamingSetting
from .preparation_dependency_service import (
    assert_can_enable_disable_prenaming,
    assert_can_modify_prenaming_config,
)


class PrenameSettingService:
    @transaction.atomic
    def get_prenaming_setting(self) -> bool:
        """Get prenaming setting."""
        p_obj = PrenamingSetting.load()
        return p_obj.enabled

    @transaction.atomic
    def set_prenaming_setting(self, enable_disable) -> None:
        """Set prenaming to the given bool.

        Raises a PlomDependencyConflict if cannot modify.
        """
        # raises a PlomDependencyConflict if fails.
        assert_can_enable_disable_prenaming()

        p_obj = PrenamingSetting.load()
        p_obj.enabled = enable_disable
        p_obj.save()

    @transaction.atomic
    def get_prenaming_config(self) -> dict:
        """Get prenaming configuration as a dict."""
        p_obj = PrenamingSetting.load()
        return {
            "enabled": p_obj.enabled,
            "xcoord": p_obj.xcoord,
            "ycoord": p_obj.ycoord,
        }

    @transaction.atomic
    def set_prenaming_coords(self, xcoord, ycoord) -> None:
        """Set prenaming box position to the given vars.

        Raises a plomDependencyConflict if the position cannot be modified.
        """
        assert_can_modify_prenaming_config()

        p_obj = PrenamingSetting.load()
        p_obj.xcoord = xcoord
        p_obj.ycoord = ycoord
        p_obj.save()

    @transaction.atomic
    def reset_prenaming_coords(self) -> None:
        """Reset prenaming coords to their defaults."""
        default_xcoord = PrenamingSetting._meta.get_field("xcoord").get_default()
        default_ycoord = PrenamingSetting._meta.get_field("ycoord").get_default()
        self.set_prenaming_coords(default_xcoord, default_ycoord)
