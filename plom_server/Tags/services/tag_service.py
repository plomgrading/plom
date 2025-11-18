# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Julian Lapenna
# Copyright (C) 2023-2025 Colin B. Macdonald

from typing import Any

from django.db.models import QuerySet

from plom_server.Mark.models import MarkingTaskTag
from plom_server.Papers.models import Paper


class TagService:
    """Class to encapsulate functions for creating and modifying tags.

    TODO: some methods are duplicated/similar in Scan services,
    specifically in ``marking_tasks.py``.  Issue #2811.
    """

    def get_tag_from_id(self, tag_id: int) -> MarkingTaskTag:
        """Get a singular tag by its id.

        Args:
            tag_id: The primary key of the tag.

        Returns:
            A tag object.
        """
        return MarkingTaskTag.objects.get(pk=tag_id)

    def get_task_tags_with_tag(self, tag_text: str) -> QuerySet[MarkingTaskTag]:
        """Get all task tags that contain the given text.

        Case insensitive. Text can be anywhere in the tag.

        Args:
            tag_text: The text to search for in the tag.

        Returns:
            A queryset of task tags.
        """
        return MarkingTaskTag.objects.filter(text__icontains=tag_text)

    def get_task_tags_with_tag_exact(self, tag_text: str) -> QuerySet[MarkingTaskTag]:
        """Get all task tags that contain the given text.

        Case insensitive. Text must match exactly.

        Args:
            tag_text: The text to search for in the tag.

        Returns:
            A queryset of task tags.
        """
        return MarkingTaskTag.objects.filter(text__in=[tag_text])

    def get_papers_from_task_tags(
        self, task_tags: QuerySet[MarkingTaskTag]
    ) -> dict[Paper, set[MarkingTaskTag]]:
        """Get all papers that have a tag with a task tag in the given queryset.

        Args:
            task_tags: A queryset of task tags.

        Returns:
            dict: keyed by papers objects whose values are their tags that are
            present in the given queryset.
        """
        papers: dict[Paper, set[MarkingTaskTag]] = {}
        for task_tag in task_tags.prefetch_related("task__paper"):
            for task in task_tag.task.all():
                if task.paper not in papers:
                    papers.update({task.paper: set()})
                papers[task.paper].add(task_tag)
        return papers

    def get_task_tags_counts(self) -> dict[MarkingTaskTag, int]:
        """Get a dictionary of the counts of each tag."""
        task_tags = MarkingTaskTag.objects.all()
        counts = {}
        for task_tag in task_tags:
            counts.update({task_tag: task_tag.task.count()})
        return counts

    # TODO: create_tag is defined in `marking_tasks.py`
    def delete_tag(self, tag_id: int) -> None:
        """Delete a tag by its id.

        Args:
            tag_id: The primary key of the tag.
        """
        tag = self.get_tag_from_id(tag_id)
        tag.delete()

    def update_tag_content(self, tag: MarkingTaskTag, content: Any) -> None:
        """Update the content of a tag."""
        for key, value in content.items():
            tag.__setattr__(key, value)
        tag.save()
