# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Colin B. Macdonald

from django.test import TestCase

from ..services import SpecificationService as serv


class SpecficiationServiceQuestionLabelTests(TestCase):
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
                2: {"pages": [3], "mark": 5, "label": "Ex.2"},
                3: {"pages": [4], "mark": 5, "label": "Q<3"},
                4: {"pages": [5], "mark": 5, "label": "Q4"},
            },
        }
        serv.store_validated_spec(spec_dict)
        return super().setUp()

    def test_qlabels(self) -> None:
        assert serv.get_question_labels() == ["Q1", "Ex.2", "Q<3", "Q4"]

    def test_qlabels_map(self) -> None:
        m = serv.get_question_labels_map()
        labels = serv.get_question_labels()
        assert len(m) == len(labels)
        for i, label in enumerate(labels):
            assert m[i + 1] == label

    def test_question_index_label_pairs(self) -> None:
        P = serv.get_question_index_label_pairs()
        m = serv.get_question_labels_map()
        assert len(P) == len(m)
        for x in P:
            assert len(x) == 2
            assert m[x[0]] == x[1]

    def test_render_qlabel_html(self) -> None:
        label, label_html = serv.get_question_label_str_and_html(1)
        assert "Q1" == label
        assert "Q1" in label_html
        label, label_html = serv.get_question_label_str_and_html(3)
        assert "Q<3" == label
        assert "Q&lt;3" in label_html

    def test_render_qlabel_html_abbr(self) -> None:
        assert "abbr" not in serv.get_question_label_str_and_html(1)[1]
        assert "abbr" in serv.get_question_label_str_and_html(2)[1]
        assert "abbr" in serv.get_question_label_str_and_html(3)[1]

    def test_render_html_list(self) -> None:
        s = serv.render_html_flat_question_label_list([1])
        assert s == "Q1"

        s = serv.render_html_flat_question_label_list([1, 4])
        assert s == "Q1, Q4"

        s = serv.render_html_flat_question_label_list([4, 1])
        assert s == "Q4, Q1"

        s = serv.render_html_flat_question_label_list([1, 3])
        assert s.startswith("Q1, ")

    def test_render_html_list_None(self) -> None:
        s = serv.render_html_flat_question_label_list([])
        assert s == "None"
        s = serv.render_html_flat_question_label_list(None)
        assert s == "None"

    def test_render_html_triplets(self) -> None:
        L = serv.get_question_html_label_triples()
        assert len(L) == 4
        for x in L:
            assert len(x) == 3
        assert L[0] == (1, "Q1", "Q1")
        assert L[3] == (4, "Q4", "Q4")
        assert L[2][0] == 3
        assert L[2][1] == "Q<3"
        assert "Q&lt;3" in L[2][2]
