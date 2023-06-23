# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2019-2021 Andrew Rechnitzer
# Copyright (C) 2020-2023 Colin B. Macdonald
# Copyright (C) 2020 Vala Vakilian
# Copyright (C) 2022 Chris Jin

"""Misc utilities related to tagging."""


def is_valid_tag_text(tag_text: str) -> bool:
    """Compare tag text against an allow list of acceptable characters.

    The allow list is currently:
    * alphanumeric characters
    * "_", "-", "+", ":", ";", "@"
    """
    allow_list = ("_", "-", "+", ":", ";", "@")
    if all(c.isalnum() or c in allow_list for c in tag_text):
        return True
    return False
