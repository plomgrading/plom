# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Edith Coates

from django.db import transaction

from Papers.models import Paper, Bundle
from ..models import TestPreparedSettingModel


@transaction.atomic
def can_status_be_set_true() -> bool:
    """Return true if the status can be changed from false to true.
    
    Currently, only a check to see if test-papers have been created - more checks could be added.
    """
    return Paper.objects.all().exists()


@transaction.atomic
def can_status_be_set_false() -> bool:
    """Return true if the status can be changed from true to false.

    Currently, only a check to see if bundles haven't been uploaded yet - subject to change.
    """
    return Bundle.objects.all().count() == 0


# We've chosen to give the above helper functions to this module because
# we want this to be the single source of truth w.r.t. the test preparation status.
# It's currently still possible to work around the setting and the various guards
# using manage.py shell and the like.


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
