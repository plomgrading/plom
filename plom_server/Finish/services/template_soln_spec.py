# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2024 Bryan Tanady

from Papers.services import SpecificationService


class TemplateSolnSpecService:
    def build_template_soln_toml(self):
        """Builds a template solution spec toml string with comments."""
        spec_dict = SpecificationService.get_the_spec()
        soln_toml = f"""# Information about the solutions:
# In general we expect that this should closely match the information
# in the test specification. The number of questions and versions must match
# the test. The test spec indicates {spec_dict['numberOfQuestions']} questions and {spec_dict['numberOfVersions']} versions.
# This template has been generated with {spec_dict['numberOfQuestions']} solutions - one for each question.
# Since plom knows the number of versions, we don't need it again in this template.
# The pages are allowed to be different from the test - both the total
# number of pages, and the pages in each question.

## numberOfPages = 6  ## <<<<< This needs editing
"""

        for q, dat in spec_dict["question"].items():
            soln_toml += f"""
[[solution]]
## pages = {dat['pages']}  ## <<<<< This needs editing
"""
        return soln_toml

    def build_soln_toml_from_test_spec(self):
        """Builds a solution spec toml string from the test spec with comments."""
        spec_dict = SpecificationService.get_the_spec()
        soln_toml = f"""# Information about the solutions:
# This toml has been generated from the test-specification with  {spec_dict['numberOfQuestions']} questions and {spec_dict['numberOfVersions']} versions.
# We assume that the number of pages, {spec_dict['numberOfPages']}, is the same as the original test
# and that the pages for each question are the same as those of the original test.

numberOfPages = {spec_dict['numberOfPages']}  # Taken from the test specification
"""

        for q, dat in spec_dict["question"].items():
            soln_toml += f"""
[[solution]]
pages = {dat['pages']}  # Taken from the test specification.
"""
        return soln_toml
