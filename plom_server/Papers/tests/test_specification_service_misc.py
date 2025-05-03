# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024-2025 Colin B. Macdonald

from django.test import TestCase
from django.core.exceptions import ObjectDoesNotExist

from ..services import SpecificationService as s


class SpecficiationServiceMiscTests(TestCase):
    def setUp(self):
        spec_dict = {
            "idPage": 1,
            "numberOfVersions": 2,
            "numberOfPages": 5,
            "totalMarks": 20,
            "numberOfQuestions": 4,
            "name": "testing",
            "longName": "Testing",
            "doNotMarkPages": [],
            "question": {
                1: {"pages": [2], "mark": 5},
                2: {"pages": [3], "mark": 5, "select": "fix"},
                3: {"pages": [4], "mark": 5, "select": "shuffle"},
                4: {"pages": [5], "mark": 5, "select": "shuffle"},
            },
        }
        s._store_validated_spec(spec_dict)
        return super().setUp()

    def test_selection_methods_dict(self) -> None:
        d = s.get_selection_method_of_all_questions()
        assert set(d.keys()) == set((1, 2, 3, 4))
        assert d[2] == "fix"
        assert d[3] == "shuffle"
        assert d[4] == "shuffle"

    def test_selection_methods_dict_default_shuffle(self) -> None:
        d = s.get_selection_method_of_all_questions()
        assert d[1] == "shuffle"

    def test_get_list_of_pages(self) -> None:
        pp = s.get_list_of_pages()
        assert pp == list(range(1, 5 + 1))

    def test_get_short_and_long_names_or_empty(self) -> None:
        assert s.get_short_and_long_names_or_empty() == ("testing", "Testing")

    def test_get_the_spec(self) -> None:
        t = s.get_the_spec()
        assert isinstance(t, dict)

    def test_get_the_spec_as_toml(self) -> None:
        t = s.get_the_spec_as_toml()
        assert isinstance(t, str)

    def test_get_the_spec_as_toml_with_code(self) -> None:
        t = s.get_the_spec_as_toml(include_public_code=True)
        assert isinstance(t, str)
        assert "publicCode" in t

    def test_get_the_spec_as_toml_without_code(self) -> None:
        t = s.get_the_spec_as_toml(include_public_code=False)
        assert isinstance(t, str)
        assert "publicCode" not in t

    def test_remove_spec(self) -> None:
        s.remove_spec()
        with self.assertRaises(ObjectDoesNotExist):
            s.remove_spec()


class SpecficiationServiceMiscNoSpecTests(TestCase):
    def test_get_list_of_pages(self) -> None:
        assert s.get_list_of_pages() == []

    def test_get_question_indices(self) -> None:
        assert s.get_question_indices() == []

    def test_get_list_of_versions(self) -> None:
        assert s.get_list_of_versions() == []

    def test_get_short_and_long_names_or_empty(self) -> None:
        assert s.get_short_and_long_names_or_empty() == ("", "")

    def test_get_the_spec(self) -> None:
        with self.assertRaises(ObjectDoesNotExist):
            s.get_the_spec()

    def test_get_the_spec_as_toml(self) -> None:
        with self.assertRaises(ObjectDoesNotExist):
            s.get_the_spec_as_toml()

    def test_remove_spec(self) -> None:
        with self.assertRaises(ObjectDoesNotExist):
            s.remove_spec()
