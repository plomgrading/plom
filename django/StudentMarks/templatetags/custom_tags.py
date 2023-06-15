# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Julian Lapenna

from django.template.defaulttags import register


@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)
