# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2024 Andrew Rechnitzer
# Copyright (C) 2023 Colin B. Macdonald

from django.db import transaction

from Preparation.models import PrenamingSetting

from Preparation.services.preparation_dependency_service import (
    assert_can_modify_prenaming,
)


class PrenameSettingService:
    @transaction.atomic
    def get_prenaming_setting(self):
        p_obj = PrenamingSetting.load()
        return p_obj.enabled

    @transaction.atomic
    def set_prenaming_setting(self, enable_disable):
        """Set prenaming to the given bool.

        Raises a PlomDependencyConflict if cannot modify.
        """
        # raises a PlomDependencyConflict if fails.
        assert_can_modify_prenaming()

        p_obj = PrenamingSetting.load()
        p_obj.enabled = enable_disable
        p_obj.save()
