# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Colin B. Macdonald

from .annotation_situations import annotation_situations


def test_homogeneous_codes():
    for code in annotation_situations.keys():
        assert isinstance(code, str)


def test_homogeneous_keys():
    keys = set(("explanation", "allowed", "warn", "dama_allowed"))
    for code, data in annotation_situations.items():
        assert set(data.keys()) == keys
