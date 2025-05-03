# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2023 Julian Lapenna
# Copyright (C) 2023-2025 Colin B. Macdonald

from django.test import TestCase
from django.db import IntegrityError
from model_bakery import baker

from ..services import PaperCreatorService, SpecificationService
from ..models import Paper, IDPage, DNMPage, QuestionPage, FixedPage, Specification


class PaperCreatorTests(TestCase):
    """Tests for services.PaperCreatorService."""

    def setUp(self):
        spec_dict = {
            "idPage": 1,
            "numberOfVersions": 2,
            "numberOfPages": 5,
            "totalMarks": 10,
            "numberOfQuestions": 2,
            "name": "papers_demo",
            "longName": "Papers Test",
            "doNotMarkPages": [2, 5],
            "question": {
                "1": {"pages": [3], "mark": 5},
                "2": {"pages": [4], "mark": 5},
            },
        }
        SpecificationService._store_validated_spec(spec_dict)
        return super().setUp()

    def get_n_models(self):
        """Helper function for getting the current number of papers/pages."""
        n_papers = Paper.objects.all().count()
        n_pages = FixedPage.objects.all().count()
        n_id = IDPage.objects.all().count()
        n_dnm = DNMPage.objects.all().count()
        n_question = QuestionPage.objects.all().count()

        return n_papers, n_pages, n_id, n_dnm, n_question

    def test_create_with_qvmapping(self) -> None:
        """Basic tests for creating paper tables."""
        qv_map = {1: 2, 2: 1}
        PaperCreatorService._create_single_paper_from_qvmapping_and_pages(1, qv_map)

        n_papers, n_pages, n_id, n_dnm, n_question = self.get_n_models()

        self.assertEqual(n_papers, 1)
        self.assertEqual(n_pages, 5)
        self.assertEqual(n_id, 1)
        self.assertEqual(n_dnm, 2)
        self.assertEqual(n_question, 2)

        paper = Paper.objects.get(paper_number=1)

        q_1 = QuestionPage.objects.get(paper=paper, question_index=1)
        self.assertEqual(q_1.version, 2)

        q_2 = QuestionPage.objects.get(paper=paper, question_index=2)
        self.assertEqual(q_2.version, 1)

    def test_remake_paper_raises(self) -> None:
        """Test creating paper tables raises an IntegrityError if called on a paper that already exists."""
        qv_map = {1: 2, 2: 1}
        PaperCreatorService._create_single_paper_from_qvmapping_and_pages(1, qv_map)

        with self.assertRaises(IntegrityError):
            PaperCreatorService._create_single_paper_from_qvmapping_and_pages(1, qv_map)

    def test_clear_papers(self) -> None:
        """Test PaperCreatorService.remove_papers_from_db()."""
        baker.make(Specification)

        paper = baker.make(Paper)
        baker.make(IDPage, paper=paper)
        baker.make(DNMPage, paper=paper)
        baker.make(QuestionPage, paper=paper)

        n_papers, n_pages, n_id, n_dnm, n_question = self.get_n_models()

        self.assertEqual(n_papers, 1)
        self.assertEqual(n_pages, 3)
        self.assertEqual(n_id, 1)
        self.assertEqual(n_dnm, 1)
        self.assertEqual(n_question, 1)

        PaperCreatorService.remove_all_papers_from_db(_testing=True)

        n_papers, n_pages, n_id, n_dnm, n_question = self.get_n_models()

        self.assertEqual(n_papers, 0)
        self.assertEqual(n_pages, 0)
        self.assertEqual(n_id, 0)
        self.assertEqual(n_dnm, 0)
        self.assertEqual(n_question, 0)
