# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2022 Brennen Chiu
# Copyright (C) 2023 Colin B. Macdonald

import sys

if sys.version_info >= (3, 10):
    from importlib import resources
else:
    import importlib_resources as resources

if sys.version_info < (3, 11):
    import tomli as tomllib
else:
    import tomllib

from django.test import TestCase

from Preparation import useful_files_for_testing as useful_files
from ..services import StagingSpecificationService
from ..models import StagingSpecification


class StagingSpecificationTests(TestCase):
    """Unit tests for StagingSpecificationService."""

    @classmethod
    def get_sample_pages(self):
        # TODO: do these refer to files in-tree?  Issue #2937
        # TODO: or are they subdirs of static?
        return {
            "0": {
                "id_page": False,
                "dnm_page": False,
                "question_page": False,
                "thumbnail": "SpecCreator/thumbnails/spec_reference/thumbnail0.png",
            },
            "1": {
                "id_page": False,
                "dnm_page": False,
                "question_page": False,
                "thumbnail": "SpecCreator/thumbnails/spec_reference/thumbnail1.png",
            },
        }

    def test_specification(self):
        """Test the specification() method."""
        spec = StagingSpecificationService()
        the_spec = spec.specification()
        self.assertEqual(type(the_spec), StagingSpecification)

    def test_reset_spec(self):
        """Test the reset_specification() method."""
        spec = StagingSpecificationService()
        the_spec = spec.specification()
        the_spec.name = "abcde"
        the_spec.longName = "abcdef"
        the_spec.pages = {"a": 1, "b": 2}
        the_spec.questions = {"c": 3, "d": 4}
        the_spec.save()

        spec.reset_specification()
        new_spec = spec.specification()
        self.assertEqual(new_spec.name, "")
        self.assertEqual(new_spec.longName, "")
        self.assertEqual(new_spec.pages, {})
        self.assertEqual(new_spec.questions, {})

    def test_get_long_name(self):
        """Test the get_long_name() method."""
        spec = StagingSpecificationService()
        the_spec = spec.specification()
        the_spec.longName = "test_longname"
        the_spec.save()
        self.assertEqual(spec.get_long_name(), the_spec.longName)

    def test_set_long_name(self):
        """Test the set_long_name() method."""
        spec = StagingSpecificationService()
        spec.set_long_name("test_longname")
        the_spec = spec.specification()
        self.assertEqual(the_spec.longName, "test_longname")

    def test_get_short_name(self):
        """Test the get_short_name() method."""
        spec = StagingSpecificationService()
        the_spec = spec.specification()
        the_spec.name = "shortname"
        the_spec.save()
        self.assertEqual(spec.get_short_name(), "shortname")

    def test_get_short_name_slug(self):
        """Test the get_short_name_slug() method."""
        spec = StagingSpecificationService()
        the_spec = spec.specification()
        the_spec.name = "this is a shortname!"
        the_spec.save()
        self.assertEqual(spec.get_short_name_slug(), "this-is-a-shortname")

    def test_set_short_name(self):
        """Test the set_short_name() method."""
        spec = StagingSpecificationService()
        spec.set_short_name("shortname")
        the_spec = spec.specification()
        self.assertEqual(the_spec.name, "shortname")

    def test_get_n_versions(self):
        """Test the get_n_versions() method."""
        spec = StagingSpecificationService()
        the_spec = spec.specification()
        the_spec.numberOfVersions = 2
        the_spec.save()
        self.assertEqual(spec.get_n_versions(), 2)

    def test_set_n_versions(self):
        """Test the set_n_versions() method."""
        spec = StagingSpecificationService()
        spec.set_n_versions(2)
        the_spec = spec.specification()
        self.assertEqual(the_spec.numberOfVersions, 2)

    def test_get_n_questions(self):
        """Test the get_n_questions() method."""
        spec = StagingSpecificationService()
        the_spec = spec.specification()
        the_spec.numberOfQuestions = 2
        the_spec.save()
        self.assertEqual(spec.get_n_questions(), the_spec.numberOfQuestions)

    def test_set_n_questions(self):
        """Test the set_n_questions() method."""
        spec = StagingSpecificationService()
        spec.set_n_questions(2)
        the_spec = spec.specification()
        self.assertEqual(the_spec.numberOfQuestions, 2)

    def test_get_total_marks(self):
        """Test the get_total_marks() method."""
        spec = StagingSpecificationService()
        the_spec = spec.specification()
        the_spec.totalMarks = 10
        the_spec.save()
        self.assertEqual(spec.get_total_marks(), the_spec.totalMarks)

    def test_set_total_marks(self):
        """Test the set_total_marks() method."""
        spec = StagingSpecificationService()
        spec.set_total_marks(10)
        the_spec = spec.specification()
        self.assertEqual(the_spec.totalMarks, 10)

    def test_set_pages(self):
        """Test the set_pages() method."""
        sample_pages = self.get_sample_pages()
        spec = StagingSpecificationService()
        spec.set_pages(2)
        the_spec = spec.specification()
        self.assertEqual(the_spec.pages, sample_pages)

    def test_set_id_page(self):
        """Test setting and resetting an ID page."""
        spec = StagingSpecificationService()
        spec.set_pages(2)

        page_dict = self.get_sample_pages()
        page_dict["1"]["id_page"] = True

        spec.set_id_page(1)
        the_spec = spec.specification()
        self.assertEqual(the_spec.pages, page_dict)

        # change it again - does it update?
        new_page_dict = self.get_sample_pages()
        new_page_dict["0"]["id_page"] = True

        spec.set_id_page(0)
        the_spec = spec.specification()
        self.assertEqual(the_spec.pages, new_page_dict)

    def test_set_do_not_mark_pages(self):
        """Test setting and resetting do-not-mark pages."""
        spec = StagingSpecificationService()
        spec.set_pages(2)

        page_dict = self.get_sample_pages()
        page_dict["0"]["dnm_page"] = True
        page_dict["1"]["dnm_page"] = True

        spec.set_do_not_mark_pages([0, 1])
        the_spec = spec.specification()
        self.assertEqual(the_spec.pages, page_dict)

        # change and check update
        new_page_dict = self.get_sample_pages()
        new_page_dict["1"]["dnm_page"] = True

        spec.set_do_not_mark_pages([1])
        the_spec = spec.specification()
        self.assertEqual(the_spec.pages, new_page_dict)

    def test_set_question_pages(self):
        """Test setting and resetting question pages."""
        spec = StagingSpecificationService()
        spec.set_pages(2)

        page_dict = self.get_sample_pages()
        page_dict["0"]["question_page"] = 1

        spec.set_question_pages([0], 1)
        the_spec = spec.specification()
        self.assertEqual(the_spec.pages, page_dict)

    def test_from_dict(self):
        """Test `StagingSpecService.create_from_dict()`."""
        with open(resources.files(useful_files) / "testing_test_spec.toml", "rb") as f:
            toml_dict = tomllib.load(f)

        spec = StagingSpecificationService()
        spec.create_from_dict(toml_dict)

        the_spec = StagingSpecification.load()
        self.assertEqual(the_spec.numberOfPages, 6)
        self.assertEqual(the_spec.numberOfVersions, 2)
        self.assertEqual(type(the_spec.questions), dict)
