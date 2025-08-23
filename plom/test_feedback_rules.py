# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024-2025 Colin B. Macdonald

from plom.feedback_rules import feedback_rules


def test_codes_are_strings() -> None:
    for code in feedback_rules.keys():
        assert isinstance(code, str)


def test_homogeneous_keys() -> None:
    # this test will need to change if the format of the rules changes
    keys = set(("explanation", "allowed", "warn", "dama_allowed", "override_allowed"))
    for code, data in feedback_rules.items():
        assert set(data.keys()) == keys


def test_explanations_are_strings() -> None:
    for code, data in feedback_rules.items():
        assert isinstance(data["explanation"], str)
