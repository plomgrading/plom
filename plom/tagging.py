# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2019-2023 Andrew Rechnitzer
# Copyright (C) 2020-2023 Colin B. Macdonald
# Copyright (C) 2020 Vala Vakilian
# Copyright (C) 2022 Chris Jin

"""Misc utilities related to tagging."""

import re

plom_valid_tag_text_description = "letters, numbers, _ - + : ; or @, but no spaces."
plom_valid_tag_text_pattern = r"^[\w\-\+\:\;\@]+$"
plom_valid_tag_text_re = re.compile(plom_valid_tag_text_pattern)


def is_valid_tag_text(tag_text: str) -> bool:
    """Compare tag text against an allow list of acceptable characters.

    The allow list is currently:
    * alphanumeric characters
    * "_", "-", "+", ":", ";", "@"
    """
    # allow_list = ("_", "-", "+", ":", ";", "@")
    if plom_valid_tag_text_re.match(tag_text):
        return True
    else:
        return False
