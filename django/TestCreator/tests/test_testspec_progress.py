from django.test import TestCase

from .. import services


class TestSpecProgressTests(TestCase):
    """Test service methods for models.TestSpecProgress"""

    def test_get_progress(self):
        """Test services.get_progress"""
        prog = services.get_progress()
        prog.is_names_completed = True
        prog.save()

        prog2 = services.get_progress()
        self.assertTrue(prog2.is_names_completed)
        self.assertFalse(prog2.is_versions_pdf_completed)
        self.assertEqual(prog2.are_questions_completed, {})

    def test_reset_progress(self):
        """Test services.reset_progress"""
        prog = services.get_progress()
        prog.is_names_completed = True
        prog.is_versions_pdf_completed = True
        prog.are_questions_completed = {'0': True, '1': True}

        prog2 = services.reset_progress()

        self.assertFalse(prog2.is_names_completed)
        self.assertFalse(prog2.is_versions_pdf_completed)
        self.assertEqual(prog2.are_questions_completed, {})

    def test_init_questions(self):
        """Test services.progress_init_questions"""
        # TODO: what happens when init_questions is called before the number of questions is set?
        services.set_num_questions(3)
        services.progress_init_questions()

        prog = services.get_progress()
        # TODO: Should probably be 1-indexed
        self.assertEqual(prog.are_questions_completed, {'0': False, '1': False, '2': False})

    def test_clear_questions(self):
        """Test services.progress_clear_questions"""
        # TODO: need a function that clears question data in both TestSpecInfo and TestSpecProgress!
        prog = services.get_progress()
        prog.are_questions_completed = {'0': True, '1': False}
        prog.save()

        services.progress_clear_questions()
        prog2 = services.get_progress()
        self.assertEqual(prog2.are_questions_completed, {})

    def test_progress_set_names(self):
        """Test services.progress_set_names"""
        services.progress_set_names(True)
        prog = services.get_progress()
        self.assertTrue(prog.is_names_completed)

    def test_progress_set_versions_pdf(self):
        """Test services.progress_set_versions_pdf"""
        services.progress_set_versions_pdf(True)
        prog = services.get_progress()
        self.assertTrue(prog.is_versions_pdf_completed)

    def test_progress_set_id_page(self):
        """Test services.progress_set_id_page"""
        services.progress_set_id_page(True)
        prog = services.get_progress()
        self.assertTrue(prog.is_id_page_completed)

    def test_progress_set_question_page(self):
        """Test services.progress_set_question_page"""
        services.progress_set_question_page(True)
        prog = services.get_progress()
        self.assertTrue(prog.is_question_page_completed)

    def test_progress_set_question_detail_page(self):
        """Test services.progress_set_question_detail_page"""
        # TODO: setting a non-existent question should throw an IndexError
        services.set_num_questions(2)
        services.progress_init_questions()
        services.progress_set_question_detail_page(1, True)
        prog = services.get_progress()
        self.assertEqual(prog.are_questions_completed, {'0': False, '1': True})

    def test_progress_set_dnm_page(self):
        """Test services.progress_set_dnm_page"""
        services.progress_set_dnm_page(True)
        prog = services.get_progress()
        self.assertTrue(prog.is_dnm_page_completed)

    def test_get_progress_dict(self):
        """Test services.get_progress_dict"""

        test_incomplete_dict = {
            'names': False,
            'upload': False,
            'id_page': False,
            'questions_page': False,
            'question_list': [],
            'dnm_page': False
        }

        prog_dict = services.get_progress_dict()
        self.assertEqual(prog_dict, test_incomplete_dict)

    def test_progress_question_list(self):
        """Test services.get_question_progress_for_template"""
        services.set_num_questions(2)
        services.progress_init_questions()
        q_list = services.get_question_progress_for_template()
        self.assertEqual(q_list, [False, False])

    def test_progress_is_everything_completed(self):
        """Test services.progress_is_everything_completed"""
        self.assertFalse(services.progress_is_everything_complete())

        services.set_num_questions(1)
        services.progress_init_questions()
        
        services.progress_set_names(True)
        services.progress_set_versions_pdf(True)
        services.progress_set_id_page(True)
        services.progress_set_question_page(True)
        services.progress_set_question_detail_page(0, True)
        services.progress_set_dnm_page(True)

        self.assertTrue(services.progress_is_everything_complete())
