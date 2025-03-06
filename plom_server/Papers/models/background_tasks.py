# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2023 Colin B. Macdonald
# Copyright (C) 2024 Andrew Rechnitzer

from django.db import models, transaction

from plom_server.Base.models import HueyTaskTracker
from plom_server.Scan.models import StagingImage


class CreateImageHueyTask(HueyTaskTracker):
    """Create an image by copying a validated StagingImage instance."""

    staging_image = models.ForeignKey(
        StagingImage, null=True, on_delete=models.SET_NULL
    )


class PopulateEvacuateDBChore(HueyTaskTracker):
    """Populate or evacuate the paper database."""

    ActionChoices = models.IntegerChoices("action", "POPULATE EVACUATE")
    POPULATE = ActionChoices.POPULATE
    EVACUATE = ActionChoices.EVACUATE
    action = models.IntegerField(
        null=False, choices=ActionChoices.choices, default=POPULATE
    )

    @classmethod
    def set_message_to_user(cls, pk, message: str):
        """Set the user-readable message string."""
        with transaction.atomic(durable=True):
            cls.objects.select_for_update().filter(pk=pk).update(message=message)
