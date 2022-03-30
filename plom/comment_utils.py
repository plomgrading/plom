# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020 Vala Vakilian
# Copyright (C) 2021-2022 Colin B. Macdonald

import random


def generate_new_comment_ID(num_of_digits=12):
    """Generate a random number string as a new comment ID.

    Args:
        num_of_digits (int, optional): Number of digits for comment ID.
            Defaults to 12.

    Returns:
        str: A 12 digit number as a string representing the new comment
            ID.
    """
    # TODO: Why string you ask ? Well because of this:
    # comIDi = QStandardItem(com["id"])
    # OverflowError: argument 1 overflowed: value must be in the range -2147483648 to 2147483647
    return str(random.randint(10**num_of_digits, 10 ** (num_of_digits + 1) - 1))
