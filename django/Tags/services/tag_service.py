# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Julian Lapenna

from Mark.models.tasks import MarkingTask, MarkingTaskTag

class TagService:
    """Class to encapsulate functions for creating and modifying tags."""

    def get_task_tags_with_tag(self, tag_text: str):
        task_tags = MarkingTaskTag.objects.filter(text__icontains=tag_text)
        return task_tags

    def get_task_tags_with_tag_exact(self, tag_text: str):
        task_tags = MarkingTaskTag.objects.filter(text__in=[tag_text])
        return task_tags

    def get_papers_from_task_tags(self, task_tags):
        papers = {}
        for task_tag in task_tags:
            for task in task_tag.task.all():
                if task.paper not in papers:
                    papers.update({task.paper: set()})
                papers[task.paper].add(task_tag.text)
        return papers
    
    def get_task_tags_counts(self):
        task_tags = MarkingTaskTag.objects.all()
        counts = {}
        for task_tag in task_tags: # this feels like n+1 query
            counts.update({task_tag.text: task_tag.task.all().count()})
        return counts