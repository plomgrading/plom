# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Julian Lapenna

import logging

from Rubrics.models import Rubric


log = logging.getLogger("RubricServer")


class TagService:
    """Class to encapsulate functions for creating and modifying tags."""

    def get_rubrics_with_tag(self, tag_name: str):
        """Return a list of rubrics that have the given tag."""
        rubrics = Rubric.objects.filter(tags__icontains=tag_name)
        return rubrics
    
    def get_rubrics_with_tag_exact(self, tag_name: str):
        """Return a list of rubrics that have the given tag."""
        print("exact activated") 
        rubrics = Rubric.objects.filter(tags__in=[tag_name])
        return rubrics