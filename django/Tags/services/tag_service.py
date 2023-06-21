# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Julian Lapenna

from Mark.models.tasks import MarkingTask, MarkingTaskTag


class TagService:
    """Class to encapsulate functions for creating and modifying tags."""

    def get_tag_from_id(self, tag_id: int):
        """Get a singular tag by its id.

        Args:
            tag_id: The primary key of the tag.

        Returns:
            A tag object.
        """
        tag = MarkingTaskTag.objects.get(pk=tag_id)
        return tag

    def get_tag_from_text(self, tag_text: str):
        """Get a singular tag by its text.

        Args:
            tag_text: The text of the tag.

        Returns:
            A tag object.
        """
        tag = MarkingTaskTag.objects.get(text=tag_text)
        return tag

    def get_task_tags_with_tag(self, tag_text: str):
        """Get all task tags that contain the given text.

        Case insensitive. Text can be anywhere in the tag.

        Args:
            tag_text: The text to search for in the tag.

        Returns:
            A queryset of task tags.
        """
        task_tags = MarkingTaskTag.objects.filter(text__icontains=tag_text)
        return task_tags

    def get_task_tags_with_tag_exact(self, tag_text: str):
        """Get all task tags that contain the given text.

        Case insensitive. Text must match exactly.

        Args:
            tag_text: The text to search for in the tag.

        Returns:
            A queryset of task tags.
        """
        task_tags = MarkingTaskTag.objects.filter(text__in=[tag_text])
        return task_tags

    def get_papers_from_task_tags(self, task_tags):
        """Get all papers that have a tag with a task tag in the given queryset.

        Args:
            task_tags: A queryset of task tags.

        Returns:
            A dictionary of papers and their tags from the given queryset.
        """
        papers = {}
        for task_tag in task_tags:
            for task in task_tag.task.all():
                if task.paper not in papers:
                    papers.update({task.paper: set()})
                papers[task.paper].add(task_tag)
        return papers

    def get_task_tags_counts(self):
        """Get a dictionary of the counts of each tag."""
        task_tags = MarkingTaskTag.objects.all()
        counts = {}
        for task_tag in task_tags:  # TODO: this feels like n+1 query
            counts.update({task_tag: task_tag.task.all().count()})
        return counts

    def delete_tag(self, tag_id: int):
        """Delete a tag by its text.

        Args:
            tag_id: The primary key of the tag.
        """
        tag = self.get_tag_from_id(tag_id)
        tag.delete()
