# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates

from django.test import TestCase
from model_bakery import baker

from Papers.services import PaperCreatorService
from Papers.models import Paper, IDPage, DNMPage, QuestionPage, BasePage, Specification


class PaperCreatorTests(TestCase):
    """
    Tests for services.PaperCreatorService
    """

    def setUp(self):
        baker.make(Specification)

    def test_clear_papers(self):
        """
        Test PaperCreatorService.remove_papers_from_db()
        """

        paper = baker.make(Paper)
        baker.make(IDPage, paper=paper)
        baker.make(DNMPage, paper=paper)
        baker.make(QuestionPage, paper=paper)

        n_papers = len(Paper.objects.all())
        n_pages = len(BasePage.objects.all())
        n_id = len(IDPage.objects.all())
        n_dnm = len(DNMPage.objects.all())
        n_question = len(QuestionPage.objects.all())

        self.assertEqual(n_papers, 1)
        self.assertEqual(n_pages, 3)
        self.assertEqual(n_id, 1)
        self.assertEqual(n_dnm, 1)
        self.assertEqual(n_question, 1)

        pcs = PaperCreatorService()
        pcs.remove_all_papers_from_db()

        n_papers = len(Paper.objects.all())
        n_pages = len(BasePage.objects.all())
        n_id = len(IDPage.objects.all())
        n_dnm = len(DNMPage.objects.all())
        n_question = len(QuestionPage.objects.all())

        self.assertEqual(n_papers, 0)
        self.assertEqual(n_pages, 0)
        self.assertEqual(n_id, 0)
        self.assertEqual(n_dnm, 0)
        self.assertEqual(n_question, 0)
