# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Aidan Murphy

from plom.cli import with_messenger

from typing import Any


@with_messenger
def create_user(
    username: str, user_groups: list[str], *, msgr
) -> dict[str, str | list[str]]:
    """Create a user account.

    Args:
        username: the username for the account.
        user_groups: the list of groups which the account should
            belong to.

    Keyword Args:
        msgr:  An active Messenger object.

    Returns:
        A dict containing the username and user groups for the created
        user, and a password reset link.
    """
    return msgr.create_user(username, user_groups)


@with_messenger
def create_user_password_reset_link(
    username: str, *, msgr
) -> dict[str, str | list[str]]:
    """Create a user account.

    Args:
        username: the username for the account.

    Keyword Args:
        msgr:  An active Messenger object.

    Returns:
        A dict containing a username and a password reset link.
    """
    return msgr.create_user_password_reset_link(username)


@with_messenger
def get_user_list(*, msgr) -> list[dict[str, Any]]:
    """Get a list of user accounts.

    Keyword Args:
        msgr:  An active Messenger object.

    Returns:
        A list of dicts with information about each user.
    """
    return msgr.get_user_list()
