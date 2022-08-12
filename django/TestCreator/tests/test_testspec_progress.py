from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from pathlib import Path
from ..services import TestSpecService, TestSpecProgressService, ReferencePDFService
from .. import models


class TestSpecProgressTests(TestCase):
    """Test services.TestSpecProgressService"""
    @classmethod
    def setUpClass(cls):
        """Init a dummy pdf file"""
        cls.dummy_file = SimpleUploadedFile('dummy.pdf', b'Test text', content_type='application/pdf')
        cls.dummy_pdf = models.ReferencePDF(filename_slug='dummy', num_pages=2, pdf=cls.dummy_file)
        return super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        """Remove all saved dummy files from disk"""

        # TODO: I guess the on delete signal doesn't get called when running tests?
        media_path = Path('TestCreator/media')
        for f in media_path.iterdir():
            f.unlink()
        return super().tearDownClass()

    def test_is_names_complete(self):
        """Test TestSpecProgressService.is_names_completed"""
        spec = TestSpecService()
        prog = TestSpecProgressService(spec)

        self.assertFalse(prog.is_names_completed())

        spec.set_long_name('long')
        spec.set_short_name('short')
        spec.set_n_versions(1)

        self.assertTrue(prog.is_names_completed())

    def test_is_pdf_page_completed(self):
        """Test TestSpecProgressService.is_pdf_page_completed"""
        spec = TestSpecService()
        prog = TestSpecProgressService(spec)

        self.assertFalse(prog.is_pdf_page_completed())

        ref_service = ReferencePDFService(spec)
        new_pdf = ref_service.create_pdf('dummy', 1, self.dummy_file)

        self.assertTrue(prog.is_pdf_page_completed())

    def test_is_id_page_completed(self):
        """Test TestSpecProgressService.is_id_page_completed"""
        spec = TestSpecService()
        spec.set_pages(self.dummy_pdf)
        prog = TestSpecProgressService(spec)

        self.assertFalse(prog.is_id_page_completed())

        spec.set_id_page(0)
        self.assertTrue(prog.is_id_page_completed())

    def test_is_question_page_completed(self):
        """Test TestSpecProgressService.is_question_page_completed"""
        spec = TestSpecService()
        prog = TestSpecProgressService(spec)

        self.assertFalse(prog.is_question_page_completed())

        spec.set_n_questions(1)
        spec.set_total_marks(1)

        self.assertTrue(prog.is_question_page_completed())

    def test_is_question_detail_page_completed(self):
        """Test TestSpecProgressService.is_question_detail_page_completed"""
        spec = TestSpecService()
        prog = TestSpecProgressService(spec)

        self.assertFalse(prog.is_question_detail_page_completed(0))

        spec.add_question(0, 'Q1', 1, False)

        self.assertTrue(prog.is_question_detail_page_completed(0))

    def test_is_dnm_page_completed(self):
        """Test TestSpecProgressService.is_dnm_page_completed"""
        spec = TestSpecService()
        prog = TestSpecProgressService(spec)

        the_spec = spec.specification()
        the_spec.dnm_page_submitted = True
        the_spec.save()

        self.assertTrue(prog.is_dnm_page_completed())

    def test_get_progress_dict(self):
        """Test services.get_progress_dict"""
        spec = TestSpecService()
        prog = TestSpecProgressService(spec)

        test_incomplete_dict = {
            'names': False,
            'upload': False,
            'id_page': False,
            'questions_page': False,
            'question_list': [],
            'dnm_page': False,
            'validate': False
        }

        prog_dict = prog.get_progress_dict()
        self.assertEqual(prog_dict, test_incomplete_dict)

