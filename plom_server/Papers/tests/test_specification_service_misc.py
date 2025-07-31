# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024-2025 Colin B. Macdonald
# Copyright (C) 2025 Aidan Murphy

from django.test import TestCase
from django.core.exceptions import ObjectDoesNotExist

from ..services import SpecificationService as s


class SpecificationServiceMiscTests(TestCase):
    def setUp(self):
        spec_dict = {
            "idPage": 1,
            "numberOfVersions": 2,
            "numberOfPages": 7,
            "totalMarks": 20,
            "numberOfQuestions": 4,
            "name": "testing",
            "longName": "Testing",
            "doNotMarkPages": [],
            "question": {
                1: {"pages": [2], "mark": 5},
                2: {"pages": [3], "mark": 5, "select": 1},
                3: {"pages": [4], "mark": 5, "select": [1, 2]},
                4: {"pages": [5, 6, 7], "mark": 5, "select": [1, 2]},
            },
        }
        s._store_validated_spec(spec_dict)
        return super().setUp()

    def test_selection_methods_dict(self) -> None:
        d = s.get_selection_method_of_all_questions()
        assert set(d.keys()) == set((1, 2, 3, 4))
        assert d[2] == [1]
        assert d[3] == [1, 2]
        assert d[4] == [1, 2]

    def test_selection_methods_dict_default(self) -> None:
        d = s.get_selection_method_of_all_questions()
        assert d[1] is None

    def test_get_list_of_pages(self) -> None:
        pp = s.get_list_of_pages()
        assert pp == list(range(1, 7 + 1))

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

    def test_get_question_pages(self) -> None:
        qidx_page_dict = s.get_question_pages()
        assert qidx_page_dict[1] == [2]
        assert qidx_page_dict[2] == [3]
        assert qidx_page_dict[3] == [4]
        assert qidx_page_dict[4] == [5, 6, 7]


class SpecificationServiceMiscNoSpecTests(TestCase):
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

    def test_get_question_pages(self) -> None:
        with self.assertRaises(ObjectDoesNotExist):
            s.get_question_pages()
