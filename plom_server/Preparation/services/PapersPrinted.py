# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Edith Coates
# Copyright (C) 2024 Andrew Rechnitzer

from django.db import transaction

from Papers.models import Paper, Bundle
from Scan.models import StagingBundle
from ..models import PapersPrintedSettingModel

from Preparation.services.preparation_dependency_service import (
    assert_can_set_papers_printed,
    assert_can_unset_papers_printed,
)


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
    return not (StagingBundle.objects.exists() or Bundle.objects.exists())


# We've chosen to give the above helper functions to this module
# because we want this to be the single source of truth w.r.t. the
# test preparation / papers printed status.  It's currently still
# possible to work around the setting and the various guards using
# manage.py shell and the like.


@transaction.atomic
def have_papers_been_printed() -> bool:
    """Return True if has been marked as 'papers_have_been_printed'."""
    setting_obj = PapersPrintedSettingModel.load()
    return setting_obj.have_printed_papers


@transaction.atomic
def set_papers_printed(status: bool):
    """Set the papers as (true) 'printed' or (false) 'yet to be printed'.

    Raises:
        PlomDependencyConflict: if status cannot be set true/false.
    """
    if status:  # trying to set papers-are-printed
        assert_can_set_papers_printed()
    else:  # trying to set papers-are-not-yet-printed
        assert_can_unset_papers_printed()

    setting_obj = PapersPrintedSettingModel.load()
    setting_obj.have_printed_papers = status
    setting_obj.save()
