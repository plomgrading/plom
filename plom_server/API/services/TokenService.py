# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Colin B. Macdonald

from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token


def drop_api_token(user_obj: User) -> None:
    """Remove the API access token for this user.

    If the token does not exist, no action taken (not an exception).
    """
    try:
        user_obj.auth_token.delete()
    except Token.DoesNotExist:
        pass
