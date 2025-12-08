# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Brennen Chiu
# Copyright (C) 2025 Colin B. Macdonald

USER_TYPE_WITH_MANAGER_CHOICES = [
    (
        "marker",
        "Marker (the standard marking account for large classes, where markers have rigidly defined roles)",
    ),
    (
        "lead_marker",
        'Lead Marker (can see and edit marking of other users, track progress, etc, implies "Marker")',
    ),
    ("identifier", "Identifier (can see ID pages and identify papers with students)"),
    ("scanner", "Scanner (can scan papers into the system)"),
    ("manager", 'Manager (overall manager account, implies "Scanner" & "Identifier")'),
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
