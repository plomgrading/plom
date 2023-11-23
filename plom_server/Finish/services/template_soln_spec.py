# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Andrew Rechnitzer

from Papers.services import SpecificationService


class TemplateSolnSpecService:
    def build_template_soln_toml(self):
        spec_dict = SpecificationService.get_the_spec()

        """Builds a template solution spec toml string with comments."""
        soln_toml = f"""
# Information about the solutions
#
# In general we expect that this should closely match the information
# in the test specification. The number of questions and versions must match
# the test.

numberOfQuestions = {spec_dict['numberOfQuestions']}   # do not change
numberOfVersions = {spec_dict['numberOfVersions']}   # do not change

# The pages are allowed to be different from the test - both the total
# number of pages, and the pages in each question.

## numberOfPages = 6  ## <<<<< This needs editing
"""
        print(spec_dict)

        for q, dat in spec_dict["question"].items():
            soln_toml += f"""
[[solution]]
## pages = {dat['pages']}  ## <<<<< This needs editing
"""
        return soln_toml
