# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Edith Coates

from django.db import transaction

from Papers.models import Paper, Bundle
from ..models import TestPreparedSettingModel


@transaction.atomic
def can_status_be_set_true() -> bool:
    return Paper.objects.all().exists()


@transaction.atomic
def can_status_be_set_false() -> bool:
    return Bundle.objects.all().count() == 0


@transaction.atomic
def is_test_prepared() -> bool:
    """Return True if the preparation has been marked as 'finished'."""
    setting_obj = TestPreparedSettingModel.load()
    return setting_obj.finished


@transaction.atomic
def set_test_prepared(status: bool):
    """Set the test preparation as 'finished' or 'in progress'.

    Raises:
        RuntimeError: if status cannot be set true/false.
    """
    if status and not can_status_be_set_true():
        raise RuntimeError("Unable to mark preparation as finished.")
    if not status and not can_status_be_set_false():
        raise RuntimeError("Unable to mark preparation as todo.")

    setting_obj = TestPreparedSettingModel.load()
    setting_obj.finished = status
    setting_obj.save()
