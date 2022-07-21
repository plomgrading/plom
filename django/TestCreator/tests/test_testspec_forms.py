from django.core.exceptions import ValidationError
from django.test import TestCase
from .. import forms


class TestSpecPDFSelectFormTests(TestCase):
    """Test the base PDF Select form"""

    def test_pdf_select_form_init(self):
        """Test the form's init method and creating fields for each page"""
        form = forms.TestSpecPDFSelectForm(num_pages=5)
        self.assertEqual(len(form.fields), 5)


class TestSpecIDPageFormTests(TestCase):
    """Test the ID page select form"""

    def test_id_page_clean(self):
        """Test TestSpecIDPageForm.clean"""
        form = forms.TestSpecIDPageForm(data={'page0': False, 'page1': True}, num_pages=2)
        valid = form.is_valid()
        self.assertTrue(valid)

    def test_id_page_multi_select_raises_error(self):
        """Test that multiple selected pages on TestSpecIDPageForm raises ValidationError"""
        form = forms.TestSpecIDPageForm(data={'page0': True, 'page1': True}, num_pages=2)
        form.is_valid()

        with self.assertRaisesMessage(ValidationError, 'Test can have only one ID page'):
            form.clean()


class TestSpecQuestionMarksFormTests(TestCase):
    """Test the question page form"""

    def test_question_marks_clean_valid(self):
        """Test TestSpecQuestionMarksForm.clean"""
        form = forms.TestSpecQuestionsMarksForm(data={'questions': 2, 'total_marks': 2})
        valid = form.is_valid()
        self.assertTrue(valid)

    def test_question_marks_too_few_marks(self):
        """Test that too few marks raises a ValidationError"""
        form = forms.TestSpecQuestionsMarksForm(data={'questions': 5, 'total_marks': 1})
        form.is_valid()

        with self.assertRaisesMessage(ValidationError, 'Number of questions should not exceed the total marks.'):
            form.clean()

    def test_question_marks_too_many_questions(self):
        """Test that too many questions raises a ValidationError"""
        form = forms.TestSpecQuestionsMarksForm(data={'questions': 51, 'total_marks': 67})
        form.is_valid()

        with self.assertRaisesMessage(ValidationError, 'Your test is too long!'):
            form.clean()
