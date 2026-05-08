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

    Note that "use_count" is a computed quantity ("annotation") not in
    the original Rubric model.  Callers will need to compute it first.
    """

    rid = django_tables2.Column("rid", linkify=True)
    # prevent newlines from rendering in json fields
    parameters = django_tables2.JSONColumn(json_dumps_kwargs={})
    # the current count includes out-of-date annotations
    # see https://gitlab.com/plom/plom/-/merge_requests/3607
    use_count = django_tables2.Column("\N{ALMOST EQUAL TO} use count")

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
            "use_count",
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
