# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Brennen Chiu
# Copyright (C) 2025 Colin B. Macdonald

USER_TYPE_WITH_MANAGER_CHOICES = [
    ("marker", "Marker"),
    ("lead_marker", "Lead Marker"),
    ("identifier", "Identifier"),
    ("scanner", "Scanner"),
    ("manager", "Manager"),
]

USER_TYPE_BULK_CHOICES = [
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
