from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from .. import services
from .. import models


class TestSpecInfoTests(TestCase):

    @classmethod
    def get_dummy_pdf(self):
        pdf_file = SimpleUploadedFile('dummy.pdf', b'Test text', content_type='application/pdf')
        pdf = models.ReferencePDF(filename_slug='dummy', num_pages=2, pdf=pdf_file)
        return pdf

    @classmethod
    def get_default_pages(self):
        return {
        "0": {
            'id_page': False,
            'dnm_page': False,
            'question_page': False,
            'thumbnail': 'thumbnails/dummy/dummy-thumbnail0.png'
        },
        "1": {
            'id_page': False,
            'dnm_page': False,
            'question_page': False,
            'thumbnail': 'thumbnails/dummy/dummy-thumbnail1.png'
        }
    }

    def test_load_spec(self):
        """Test loading the TestSpecInfo object"""

        spec = services.load_spec()
        self.assertEqual(spec.pk, 1)
        self.assertEqual(spec.long_name, '')

    def test_testspec_persistence(self):
        """Test that editing a loaded spec object saves to the database"""
        spec = services.load_spec()

        spec.long_name = 'test_longname'
        spec.save()

        new_spec = services.load_spec()
        self.assertEqual(new_spec.pk, 1)
        self.assertEqual(new_spec.long_name, 'test_longname')

    def test_reset_spec(self):
        """Test services.reset_spec"""
        spec = services.load_spec()
        spec.long_name = 'long_name'
        spec.short_name = 'shortname'
        spec.n_versions = 2

        spec = services.reset_spec()
        self.assertEqual(spec.long_name, '')
        self.assertEqual(spec.short_name, '')
        self.assertEqual(spec.n_versions, 0)

    def test_get_long_name(self):
        """Test services.get_long_name"""
        spec = services.load_spec()
        spec.long_name = 'test_longname'
        spec.save()
        self.assertEqual(services.get_long_name(), spec.long_name)

    def test_set_long_name(self):
        """Test services.set_long_name"""
        services.set_long_name('test_longname')
        spec = services.load_spec()
        self.assertEqual(spec.long_name, 'test_longname')

    def test_get_short_name(self):
        """Test services.get_short_name"""
        spec = services.load_spec()
        spec.short_name = 'shortname'
        spec.save()
        self.assertEqual(services.get_short_name(), 'shortname')

    def test_set_short_name(self):
        """Test services.set_short_name"""

        # This fails if the spec is instantiated before calling set_short_name
        # So the references don't update when then underlying database is updated?
        # Something to think about...
        services.set_short_name('shortname')
        spec = services.load_spec()
        self.assertEqual(spec.short_name, 'shortname')

    def test_get_num_versions(self):
        """Test services.get_num_versions"""
        spec = services.load_spec()
        spec.n_versions = 2
        spec.save()
        self.assertEqual(services.get_num_versions(), 2)

    def test_set_num_versions(self):
        """Test services.set_num_versions"""
        services.set_num_versions(2)
        spec = services.load_spec()
        self.assertEqual(spec.n_versions, 2)

    def test_get_num_questions(self):
        """Test services.get_num_questions"""
        spec = services.load_spec()
        spec.n_questions = 2
        spec.save()
        self.assertEqual(services.get_num_questions(), spec.n_questions)

    def test_set_num_questions(self):
        """Test services.set_num_questions"""
        services.set_num_questions(2)
        spec = services.load_spec()
        self.assertEqual(spec.n_questions, 2)

    def test_get_total_marks(self):
        """Test services.get_total_marks"""
        spec = services.load_spec()
        spec.total_marks = 10
        spec.save()
        self.assertEqual(services.get_total_marks(), spec.total_marks)

    def test_set_total_marks(self):
        """Test services.set_total_marks"""
        services.set_total_marks(10)
        spec = services.load_spec()
        self.assertEqual(spec.total_marks, 10)

    def test_set_pages(self):
        """Test services.set_pages"""
        pdf = self.get_dummy_pdf()
        services.set_pages(pdf)

        spec = services.load_spec()
        self.assertEqual(spec.pages, self.get_default_pages())


    def test_set_id_page(self):
        """Test setting and resetting an ID page"""
        pdf = self.get_dummy_pdf()
        services.set_pages(pdf)

        page_dict = self.get_default_pages()
        page_dict['1']['id_page'] = True

        services.set_id_page(1)
        spec = services.load_spec()
        self.assertEqual(spec.pages, page_dict)

        # change it again - does it update?
        new_page_dict = self.get_default_pages()
        new_page_dict['0']['id_page'] = True

        services.set_id_page(0)
        spec = services.load_spec()
        self.assertEqual(spec.pages, new_page_dict)

    def test_set_do_not_mark_pages(self):
        """Test setting and resetting do-not-mark pages"""
        pdf = self.get_dummy_pdf()
        services.set_pages(pdf)

        page_dict = self.get_default_pages()
        page_dict['0']['dnm_page'] = True
        page_dict['1']['dnm_page'] = True

        services.set_do_not_mark_pages([0, 1])
        spec = services.load_spec()
        self.assertEqual(spec.pages, page_dict)

        # change and check update
        new_page_dict = self.get_default_pages()
        new_page_dict['1']['dnm_page'] = True

        services.set_do_not_mark_pages([1])
        spec = services.load_spec()
        self.assertEqual(spec.pages, new_page_dict)

    def test_set_question_pages(self):
        """ Test setting and resetting question pages"""
        pdf = self.get_dummy_pdf()
        services.set_pages(pdf)

        page_dict = self.get_default_pages()
        page_dict['0']['question_page'] = 1

        services.set_question_pages([0], 1)
        spec = services.load_spec()
        self.assertEqual(spec.pages, page_dict)
