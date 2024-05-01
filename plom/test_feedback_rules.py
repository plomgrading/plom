# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Colin B. Macdonald

from .feedback_rules import feedback_rules


def test_codes_are_strings():
    for code in feedback_rules.keys():
        assert isinstance(code, str)


def test_homogeneous_keys():
    keys = set(("explanation", "allowed", "warn", "dama_allowed"))
    for code, data in feedback_rules.items():
        assert set(data.keys()) == keys


def test_explanations_are_strings():
    for code, data in feedback_rules.items():
        assert isinstance(data["explanation"], str)
