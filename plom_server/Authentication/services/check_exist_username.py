# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Brennen Chiu
# Copyright (C) 2023 Colin B. Macdonald

from random_username.generate import generate_username


def check_username(username, exist_list, new_list) -> str:
    if username not in exist_list + new_list:
        return username
    else:
        username = generate_username()
        username = "".join(username)
        return check_username(username, exist_list, new_list)
