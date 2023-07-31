# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2023 Julian Lapenna

from model_bakery import baker
from django.test import TestCase

from SpecCreator import services
from .. import models


class TestSpecQuestionTests(TestCase):
    """Test services code for models.TestSpecQuestion."""

    @classmethod
    def get_default_pages(self):
        return {
            "0": {
                "id_page": False,
                "dnm_page": False,
                "question_page": False,
                "thumbnail": "thumbnails/dummy/dummy-thumbnail0.png",
            },
            "1": {
                "id_page": False,
                "dnm_page": False,
                "question_page": False,
                "thumbnail": "thumbnails/dummy/dummy-thumbnail1.png",
            },
        }

    def test_create_question(self):
        """Test `TestSpecQuestionService.create_question`."""
        spec = services.TestSpecService()
        qserv = services.TestSpecQuestionService(0, spec)
        q1 = qserv.create_question("Q1", 1, False)
        self.assertEqual(q1.index, 0)
        self.assertEqual(q1.label, "Q1")
        self.assertEqual(q1.mark, 1)
        self.assertEqual(q1.shuffle, False)

    def test_remove_question(self):
        """Test `TestSpecQuestionService.remove_question`."""
        spec = services.TestSpecService()
        qserv = services.TestSpecQuestionService(1, spec)
        q1 = models.TestSpecQuestion(index=1, label="Q1", mark=1, shuffle=False)
        q1.save()

        qserv.remove_question()
        self.assertEqual(models.TestSpecQuestion.objects.all().count(), 0)

    def test_remove_question_update_spec(self):
        """Test that calling remove_question will update the pages in `models.TestSpecInfo`."""
        spec = services.TestSpecService()
        qserv = services.TestSpecQuestionService(1, spec)
        q1 = models.TestSpecQuestion(index=1, label="Q1", mark=1, shuffle=False)
        q1.save()

        the_spec = spec.specification()
        the_spec.pages = self.get_default_pages()
        the_spec.pages["1"]["question_page"] = 1
        the_spec.save()

        qserv.remove_question()

        # You'll have calling load_spec() every time you want to lookup the most recent values
        the_spec = spec.specification()
        self.assertEqual(the_spec.pages["1"]["question_page"], False)

    def test_clear_questions(self):
        """Test `TestSpecService.clear_questions`."""
        spec = services.TestSpecService()
        spec.add_question(1, "Q1", 1, False)
        spec.add_question(2, "Q2", 1, False)
        spec.add_question(3, "Q3", 1, False)
        spec.set_n_questions(3)

        spec.clear_questions()
        self.assertEqual(models.TestSpecQuestion.objects.all().count(), 0)

    def test_total_assigned_marks(self):
        """Test `TestSpecService.get_total_assigned_marks`."""
        q1 = baker.make(models.TestSpecQuestion, mark=5)
        q2 = baker.make(models.TestSpecQuestion, mark=5)

        spec = services.TestSpecService()
        total_so_far = spec.get_total_assigned_marks()
        self.assertEqual(total_so_far, 10)

    def test_get_available_marks(self):
        """Test `TestSpecService.get_available_marks`."""
        spec = services.TestSpecService()
        spec.set_total_marks(10)
        q1 = baker.make(models.TestSpecQuestion, mark=4, index=0)
        spec.questions[0] = services.TestSpecQuestionService(0, spec)
        available = spec.get_available_marks(0)
        self.assertEqual(available, 10)

    def test_get_marks_assigned_to_other_questions(self):
        """Test `TestSpecQuestionService.get_marks_assigned_to_other_questions`."""
        spec = services.TestSpecService()
        spec.add_question(0, "", 5, False)
        spec.add_question(1, "", 3, False)
        spec.add_question(2, "", 2, False)
        qserv = spec.questions[2]
        marks_to_others = qserv.get_marks_assigned_to_other_questions()
        self.assertEqual(marks_to_others, 8)

    def test_other_questions_total(self):
        """Test `TestSpecService.get_available_marks` with previously assigned values."""
        spec = services.TestSpecService()
        spec.set_total_marks(10)
        q1 = baker.make(models.TestSpecQuestion, mark=7, index=0)
        spec.questions[0] = services.TestSpecQuestionService(0, spec)
        q2 = baker.make(models.TestSpecQuestion, mark=3, index=1)
        spec.questions[1] = services.TestSpecQuestionService(1, spec)

        # let's say we're on the detail page for question 2
        available = spec.get_available_marks(q2.index)
        self.assertEqual(available, 3)
