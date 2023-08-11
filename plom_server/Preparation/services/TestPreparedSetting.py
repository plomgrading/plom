# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Edith Coates

from django.db import transaction

from ..models import TestPreparedSettingModel


@transaction.atomic
def is_test_prepared() -> bool:
    """Return True if the preparation has been marked as 'finished'."""
    setting_obj = TestPreparedSettingModel.load()
    return setting_obj.finished


@transaction.atomic
def set_test_prepared(status: bool):
    """Set the test preparation as 'finished' or 'in progress'."""
    setting_obj = TestPreparedSettingModel.load()
    setting_obj.finished = status
    setting_obj.save()
