# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2023 Colin B. Macdonald

from django.core.exceptions import ValidationError
from django.test import TestCase
from model_bakery import baker

from ..services import TestSpecService
from .. import forms
from .. import models


class TestSpecPDFSelectFormTests(TestCase):
    """Test the base PDF Select form."""

    def test_pdf_select_form_init(self):
        """Test the form's init method and creating fields for each page."""
        form = forms.TestSpecPDFSelectForm(num_pages=5)
        self.assertEqual(len(form.fields), 5)


class TestSpecIDPageFormTests(TestCase):
    """Test the ID page select form."""

    def test_id_page_clean(self):
        """Test TestSpecIDPageForm.clean."""
        form = forms.TestSpecIDPageForm(
            data={"page0": False, "page1": True}, num_pages=2
        )
        valid = form.is_valid()
        self.assertTrue(valid)

    def test_id_page_multi_select_raises_error(self):
        """Test that multiple selected pages on TestSpecIDPageForm raises ValidationError."""
        form = forms.TestSpecIDPageForm(
            data={"page0": True, "page1": True}, num_pages=2
        )
        form.is_valid()

        with self.assertRaisesMessage(
            ValidationError, "Test can have only one ID page"
        ):
            form.clean()


class TestSpecQuestionMarksFormTests(TestCase):
    """Test the question page form."""

    def test_question_marks_clean_valid(self):
        """Test TestSpecQuestionMarksForm.clean."""
        form = forms.TestSpecQuestionsMarksForm(data={"questions": 2, "total_marks": 2})
        valid = form.is_valid()
        self.assertTrue(valid)

    def test_question_marks_too_few_marks(self):
        """Test that too few marks raises a ValidationError."""
        form = forms.TestSpecQuestionsMarksForm(data={"questions": 5, "total_marks": 1})
        form.is_valid()

        with self.assertRaisesMessage(
            ValidationError, "Number of questions should not exceed the total marks."
        ):
            form.clean()

    def test_question_marks_too_many_questions(self):
        """Test that too many questions raises a ValidationError."""
        form = forms.TestSpecQuestionsMarksForm(
            data={"questions": 51, "total_marks": 67}
        )
        form.is_valid()

        with self.assertRaisesMessage(ValidationError, "Your test is too long!"):
            form.clean()


class TestSpecQuestionFormTests(TestCase):
    """Test the question detail form."""

    def test_question_clean_valid(self):
        """Test TestSpecQuestionForm.clean."""
        form = forms.TestSpecQuestionForm(
            data={
                "label": "Q1",
                "mark": 2,
                "shuffle": "F",
                "page0": False,
                "page1": True,
            },
            num_pages=2,
            q_idx=1,
        )

        spec = TestSpecService()
        spec.set_total_marks(2)
        valid = form.is_valid()
        self.assertTrue(valid)

    def test_question_too_many_marks(self):
        """Test that too many marks for the question will raise a ValidationError."""
        form = forms.TestSpecQuestionForm(
            data={"label": "Q1", "mark": 5, "shuffle": "F", "page0": True},
            num_pages=1,
            q_idx=1,
        )

        spec = TestSpecService()
        spec.set_total_marks(2)
        form.is_valid()

        with self.assertRaisesMessage(
            ValidationError, "Question cannot have more marks than the test."
        ):
            form.clean()

    def test_question_no_selected_page(self):
        """Test that selecting no pages for the question raises a ValidationError."""
        form = forms.TestSpecQuestionForm(
            data={
                "label": "Q1",
                "mark": 2,
                "shuffle": "F",
                "page0": False,
                "page1": False,
            },
            num_pages=2,
            q_idx=1,
        )

        spec = TestSpecService()
        spec.set_total_marks(2)
        form.is_valid()

        with self.assertRaisesMessage(
            ValidationError, "At least one page must be selected."
        ):
            form.clean()

    def test_question_consecutive_pages(self):
        """Test that page selection with a gap will raise a ValidationError."""
        form = forms.TestSpecQuestionForm(
            data={
                "label": "Q1",
                "mark": 2,
                "shuffle": "F",
                "page0": False,
                "page1": True,
                "page2": False,
                "page3": True,
            },
            num_pages=4,
            q_idx=1,
        )

        spec = TestSpecService()
        spec.set_total_marks(2)
        form.is_valid()

        with self.assertRaisesMessage(
            ValidationError, "Question pages must be consecutive."
        ):
            form.clean()

    def test_question_no_earlier_pages(self):
        """Test that assigning questions to pages before earlier questions will raise a ValidationError."""
        q1 = baker.make(models.TestSpecQuestion, index=1)
        q2 = baker.make(models.TestSpecQuestion, index=2)
        pdf = baker.make(models.ReferencePDF, num_pages=2)

        spec = TestSpecService()
        spec.set_pages(pdf)
        spec.set_n_questions(2)
        spec.set_total_marks(2)
        spec.set_question_pages([1], 1)

        form = forms.TestSpecQuestionForm(
            data={
                "label": "Q2",
                "mark": 1,
                "shuffle": "F",
                "page0": True,
                "page1": False,
            },
            num_pages=2,
            q_idx=2,
        )
        form.is_valid()

        with self.assertRaisesMessage(
            ValidationError, "Question 2 cannot come before question 1."
        ):
            form.clean()
