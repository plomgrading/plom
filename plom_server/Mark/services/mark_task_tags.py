# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2023 Colin B. Macdonald
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2023 Julian Lapenna
# Copyright (C) 2023 Natalie Balashov

"""Services for marking task tags."""

from typing import List

from django.db import transaction
from django.db.models import QuerySet

from ..models import MarkingTask, MarkingTaskTag


class MarkingTaskTagService:
    @transaction.atomic
    def get_tag_texts_for_task(self, task: MarkingTask) -> List[str]:
        """Get the text of all tags assigned to this marking task."""
        return list(
            task.markingtasktag_set.order_by("text").values_list("text", flat=True)
        )

    @transaction.atomic
    def get_tags_for_task(self, task: MarkingTask) -> QuerySet[MarkingTaskTag]:
        """Get all tags assigned to this marking task."""
        return task.markingtasktag_set.all().order_by("text")

    @transaction.atomic
    def get_all_marking_task_tags(self) -> QuerySet[MarkingTaskTag]:
        """Get all tags."""
        return MarkingTaskTag.objects.all().order_by("text")

    @transaction.atomic
    def add_tag_to_task(self, tag_pk: int, task_pk: int):
        """Add existing tag with given pk to the marking task with given pk."""
        try:
            the_task = MarkingTask.objects.select_for_update().get(pk=task_pk)
            the_tag = MarkingTaskTag.objects.get(pk=tag_pk)
        except (MarkingTask.DoesNotExist, MarkingTaskTag.DoesNotExist):
            raise ValueError("Cannot find task or tag with given pk")
        the_task.markingtasktag_set.add(the_tag)
        the_task.save()

    @transaction.atomic
    def remove_tag_from_task(self, tag_pk: int, task_pk: int):
        """Add existing tag with given pk to the marking task with given pk."""
        try:
            the_task = MarkingTask.objects.select_for_update().get(pk=task_pk)
            the_tag = MarkingTaskTag.objects.get(pk=tag_pk)
        except (MarkingTask.DoesNotExist, MarkingTaskTag.DoesNotExist):
            raise ValueError("Cannot find task or tag with given pk")
        the_task.markingtasktag_set.remove(the_tag)
        the_task.save()
