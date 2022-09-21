from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from ..services import TestSpecService
from .. import models


class TestSpecInfoTests(TestCase):
    @classmethod
    def get_dummy_pdf(self):
        pdf_file = SimpleUploadedFile(
            "dummy.pdf", b"Test text", content_type="application/pdf"
        )
        pdf = models.ReferencePDF(filename_slug="dummy", num_pages=2, pdf=pdf_file)
        return pdf

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

    def test_load_spec(self):
        """Test loading the TestSpecService object"""

        spec = TestSpecService()
        the_spec = spec.specification()
        self.assertEqual(the_spec.pk, 1)
        self.assertEqual(the_spec.long_name, "")

    def test_testspec_persistence(self):
        """Test that editing a loaded spec object saves to the database"""
        spec = TestSpecService()
        the_spec = spec.specification()

        the_spec.long_name = "test_longname"
        the_spec.save()

        new_spec = spec.specification()
        self.assertEqual(new_spec.pk, 1)
        self.assertEqual(new_spec.long_name, "test_longname")

    def test_reset_spec(self):
        """Test TestSpecService.reset_specification"""
        spec = TestSpecService()
        the_spec = spec.specification()
        the_spec.long_name = "long_name"
        the_spec.short_name = "shortname"
        the_spec.n_versions = 2

        new_spec = spec.reset_specification()
        self.assertEqual(new_spec.long_name, "")
        self.assertEqual(new_spec.short_name, "")
        self.assertEqual(new_spec.n_versions, 0)

    def test_get_long_name(self):
        """Test TestSpecService.get_long_name"""
        spec = TestSpecService()
        the_spec = spec.specification()
        the_spec.long_name = "test_longname"
        the_spec.save()
        self.assertEqual(spec.get_long_name(), the_spec.long_name)

    def test_set_long_name(self):
        """Test TestSpecService.set_long_name"""
        spec = TestSpecService()
        spec.set_long_name("test_longname")
        the_spec = spec.specification()
        self.assertEqual(the_spec.long_name, "test_longname")

    def test_get_short_name(self):
        """Test TestSpecService.get_short_name"""
        spec = TestSpecService()
        the_spec = spec.specification()
        the_spec.short_name = "shortname"
        the_spec.save()
        self.assertEqual(spec.get_short_name(), "shortname")

    def test_set_short_name(self):
        """Test TestSpecService.set_short_name"""

        # This fails if the spec is instantiated before calling set_short_name
        # So the references don't update when then underlying database is updated?
        # Something to think about...
        spec = TestSpecService()
        spec.set_short_name("shortname")
        the_spec = spec.specification()
        self.assertEqual(the_spec.short_name, "shortname")

    def test_get_n_versions(self):
        """Test TestSpecService.get_n_versions"""
        spec = TestSpecService()
        the_spec = spec.specification()
        the_spec.n_versions = 2
        the_spec.save()
        self.assertEqual(spec.get_n_versions(), 2)

    def test_set_n_versions(self):
        """Test TestSpecService.set_n_versions"""
        spec = TestSpecService()
        spec.set_n_versions(2)
        the_spec = spec.specification()
        self.assertEqual(the_spec.n_versions, 2)

    def test_get_n_questions(self):
        """Test TestSpecService.get_n_questions"""
        spec = TestSpecService()
        the_spec = spec.specification()
        the_spec.n_questions = 2
        the_spec.save()
        self.assertEqual(spec.get_n_questions(), the_spec.n_questions)

    def test_set_n_questions(self):
        """Test TestSpecService.set_n_questions"""
        spec = TestSpecService()
        spec.set_n_questions(2)
        the_spec = spec.specification()
        self.assertEqual(the_spec.n_questions, 2)

    def test_get_total_marks(self):
        """Test TestSpecService.get_total_marks"""
        spec = TestSpecService()
        the_spec = spec.specification()
        the_spec.total_marks = 10
        the_spec.save()
        self.assertEqual(spec.get_total_marks(), the_spec.total_marks)

    def test_set_total_marks(self):
        """Test TestSpecService.set_total_marks"""
        spec = TestSpecService()
        spec.set_total_marks(10)
        the_spec = spec.specification()
        self.assertEqual(the_spec.total_marks, 10)

    def test_set_pages(self):
        """Test TestSpecService.set_pages"""
        pdf = self.get_dummy_pdf()
        spec = TestSpecService()
        spec.set_pages(pdf)

        the_spec = spec.specification()
        self.assertEqual(the_spec.pages, self.get_default_pages())

    def test_set_id_page(self):
        """Test setting and resetting an ID page"""
        pdf = self.get_dummy_pdf()
        spec = TestSpecService()
        spec.set_pages(pdf)

        page_dict = self.get_default_pages()
        page_dict["1"]["id_page"] = True

        spec.set_id_page(1)
        the_spec = spec.specification()
        self.assertEqual(the_spec.pages, page_dict)

        # change it again - does it update?
        new_page_dict = self.get_default_pages()
        new_page_dict["0"]["id_page"] = True

        spec.set_id_page(0)
        the_spec = spec.specification()
        self.assertEqual(the_spec.pages, new_page_dict)

    def test_set_do_not_mark_pages(self):
        """Test setting and resetting do-not-mark pages"""
        pdf = self.get_dummy_pdf()
        spec = TestSpecService()
        spec.set_pages(pdf)

        page_dict = self.get_default_pages()
        page_dict["0"]["dnm_page"] = True
        page_dict["1"]["dnm_page"] = True

        spec.set_do_not_mark_pages([0, 1])
        the_spec = spec.specification()
        self.assertEqual(the_spec.pages, page_dict)

        # change and check update
        new_page_dict = self.get_default_pages()
        new_page_dict["1"]["dnm_page"] = True

        spec.set_do_not_mark_pages([1])
        the_spec = spec.specification()
        self.assertEqual(the_spec.pages, new_page_dict)

    def test_set_question_pages(self):
        """Test setting and resetting question pages"""
        pdf = self.get_dummy_pdf()
        spec = TestSpecService()
        spec.set_pages(pdf)

        page_dict = self.get_default_pages()
        page_dict["0"]["question_page"] = 1

        spec.set_question_pages([0], 1)
        the_spec = spec.specification()
        self.assertEqual(the_spec.pages, page_dict)
