# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2023 Brennen Chiu
# Copyright (C) 2023-2026 Colin B. Macdonald
# Copyright (C) 2023 Julian Lapenna
# Copyright (C) 2023 Natalie Balashov
# Copyright (C) 2024 Aidan Murphy
# Copyright (C) 2024 Aden Chan

import django_tables2

from .models import Rubric


class RubricTable(django_tables2.Table):
    """Table class for displaying rubrics.

    More information on django-tables2 can be found at:
    https://django-tables2.readthedocs.io/en/latest
    """

    rid = django_tables2.Column("rid", linkify=True)
    # prevent newlines from rendering in json fields
    parameters = django_tables2.JSONColumn(json_dumps_kwargs={})
    # TODO: issue #3648, seeking a way to display how often they are used
    # times_used = django_tables2.Column(
    #     verbose_name="# Used",
    #     accessor="get_usage_count",
    #     orderable=False
    # )
    # TODO: accessor="annotations__xxx__xxx" somehow?
    # TODO: i want to make sortable but it just crashes unless orderable=False

    class Meta:
        model = Rubric

        row_attrs = {
            "class": lambda record: "opacity-25" if not record.published else ""
        }

        # which fields to include in the table.  Or omit for all fields
        # and use sequence = (...) to control the order.
        fields = (
            "rid",
            "display_delta",
            "text",
            "user",
            "last_modified",
            "modified_by_user",
            "revision",
            "subrevision",
            "published",
            "kind",
            "system_rubric",
            "question_index",
            "versions",
            "parameters",
            "tags",
            "pedagogy_tags",
        )
