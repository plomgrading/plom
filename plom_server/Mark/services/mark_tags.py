# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2023 Colin B. Macdonald
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2023 Julian Lapenna
# Copyright (C) 2023 Natalie Balashov

"""Services for marking task tags."""

from typing import List

from django.db import transaction

from ..models import MarkingTask


@transaction.atomic
def get_tag_texts_for_task(task: MarkingTask) -> List[str]:
    """Get the text of all tags assigned to this marking task."""
    tags = task.markingtasktag_set.all()
    return [tag.text for tag in tags]
