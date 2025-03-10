# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Brennen Chiu

USER_TYPE_WITH_MANAGER_CHOICES = [
    ("marker", "Marker"),
    ("scanner", "Scanner"),
    ("manager", "Manager"),
]

USER_TYPE_WITHOUT_MANAGER_CHOICES = [
    ("marker", "Marker"),
    ("scanner", "Scanner"),
]

USERNAME_CHOICES = [
    ("basic", "Basic numbered usernames"),
    (
        "funky",
        "\N{LEFT DOUBLE QUOTATION MARK}Funky\N{RIGHT DOUBLE QUOTATION MARK} usernames (such as \N{LEFT DOUBLE QUOTATION MARK}hungryHeron8\N{RIGHT DOUBLE QUOTATION MARK})",
    ),
]
