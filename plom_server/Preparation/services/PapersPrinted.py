# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Edith Coates
# Copyright (C) 2024-2025 Andrew Rechnitzer
# Copyright (C) 2025 Colin B. Macdonald

from django.db import transaction

from ..models import PapersPrintedSettingModel
from ..services.preparation_dependency_service import (
    assert_can_set_papers_printed,
    assert_can_unset_papers_printed,
)


@transaction.atomic
def have_papers_been_printed() -> bool:
    """Return True if has been marked as 'papers_have_been_printed'."""
    setting_obj = PapersPrintedSettingModel.load()
    return setting_obj.have_printed_papers


@transaction.atomic(durable=True)
def set_papers_printed(status: bool, *, ignore_dependencies: bool = False):
    """Set the papers as (true) 'printed' or (false) 'yet to be printed'.

    Note that as a side-effect when setting
      * true => will create system rubrics
      * false => will delete all existing rubrics

    Args:
        status: True to set printed, False to set unprinted.

    Keyword Args:
        ignore_dependencies: set this for testing purposes, so that one
            can set papers-printed=true, without actually building pdfs.
            Setting this also means rubrics will not be produced.

    Raises:
        PlomDependencyConflict: if status cannot be set true/false.
    """
    if ignore_dependencies:
        pass
    else:
        if status:  # trying to set papers-are-printed
            assert_can_set_papers_printed()
        else:  # trying to set papers-are-not-yet-printed
            assert_can_unset_papers_printed()

    setting_obj = PapersPrintedSettingModel.load()
    setting_obj.have_printed_papers = status
    setting_obj.save()

    if ignore_dependencies:
        return

    from plom_server.Rubrics.services import RubricService
    from plom_server.Scan.services import ForgiveMissingService

    if status:
        RubricService().init_rubrics()
        ForgiveMissingService.create_system_bundle_of_substitute_pages()
    else:
        RubricService()._erase_all_rubrics()
        ForgiveMissingService.erase_all_substitute_images_and_their_bundle()
