from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from . import services
from . import models


class TestTestSpecInfo(TestCase):

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
        spec = services.load_spec()
        self.assertEquals(spec.pk, 1)
        self.assertEquals(spec.long_name, '')

        # give it a long name, test persistence
        spec.long_name = 'blah'
        spec.save()

        new_spec = services.load_spec()
        self.assertEquals(new_spec.pk, 1)
        self.assertEquals(new_spec.long_name, 'blah')

    def test_get_long_name(self):
        spec = services.load_spec()
        spec.long_name = 'test'
        spec.save()
        self.assertEquals(services.get_long_name(), spec.long_name)

    def test_set_long_name(self):
        services.set_long_name('blah')
        spec = services.load_spec()
        self.assertEquals(spec.long_name, 'blah')

    def test_get_short_name(self):
        spec = services.load_spec()
        spec.short_name = 't'
        spec.save()
        self.assertEquals(services.get_short_name(), spec.short_name)

    def test_set_short_name(self):
        # This fails if the spec is instantiated before calling set_short_name
        # So the references don't update when then underlying database is updated?
        # Something to think about...
        services.set_short_name('t')
        spec = services.load_spec()
        self.assertEquals(spec.short_name, 't')

    def test_get_num_questions(self):
        spec = services.load_spec()
        spec.n_questions = 2
        spec.save()
        self.assertEquals(services.get_num_questions(), spec.n_questions)

    def test_set_num_questions(self):
        services.set_num_questions(2)
        spec = services.load_spec()
        self.assertEquals(spec.n_questions, 2)

    def test_get_total_marks(self):
        spec = services.load_spec()
        spec.total_marks = 10
        spec.save()
        self.assertEquals(services.get_total_marks(), spec.total_marks)

    def test_set_total_marks(self):
        services.set_total_marks(10)
        spec = services.load_spec()
        self.assertEquals(spec.total_marks, 10)

    def test_set_pages(self):
        pdf = self.get_dummy_pdf()
        services.set_pages(pdf)

        spec = services.load_spec()
        self.assertEquals(spec.pages, self.get_default_pages())

    def test_set_id_page(self):
        pdf = self.get_dummy_pdf()
        services.set_pages(pdf)

        page_dict = self.get_default_pages()
        page_dict['1']['id_page'] = True

        services.set_id_page(1)
        spec = services.load_spec()
        self.assertEquals(spec.pages, page_dict)

        # change it again - does it update?
        new_page_dict = self.get_default_pages()
        new_page_dict['0']['id_page'] = True

        services.set_id_page(0)
        spec = services.load_spec()
        self.assertEquals(spec.pages, new_page_dict)

    def test_set_do_not_mark_pages(self):
        pdf = self.get_dummy_pdf()
        services.set_pages(pdf)

        page_dict = self.get_default_pages()
        page_dict['0']['dnm_page'] = True
        page_dict['1']['dnm_page'] = True

        services.set_do_not_mark_pages([0, 1])
        spec = services.load_spec()
        self.assertEquals(spec.pages, page_dict)

        # change and check update
        new_page_dict = self.get_default_pages()
        new_page_dict['1']['dnm_page'] = True

        services.set_do_not_mark_pages([1])
        spec = services.load_spec()
        self.assertEquals(spec.pages, new_page_dict)

    def test_set_question_pages(self):
        pdf = self.get_dummy_pdf()
        services.set_pages(pdf)

        page_dict = self.get_default_pages()
        page_dict['0']['question_page'] = 1

        services.set_question_pages([0], 1)
        spec = services.load_spec()
        self.assertEquals(spec.pages, page_dict)
