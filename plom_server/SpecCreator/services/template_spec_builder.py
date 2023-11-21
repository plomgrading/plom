# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Andrew Rechnitzer


class TemplateSpecBuilderService:
    def build_template_toml(
        self, longName=None, shortName=None, pages=2, questions=1, versions=1, score=5
    ):
        """Builds a template toml string with comments."""
        spec_toml = f"""
# Two human-readable names of the test - one long, one short.
longName = "{longName}"

# The short name must be alphanumeric without spaces. Underscore, hyphens and periods are okay.
name = "{shortName}"

# must have an even number of pages and print double-sided
numberOfPages = {pages}
numberOfQuestions = {questions}
numberOfVersions = {versions}
totalMarks = {score}

# Your test must have exactly one id-page this is usually page 1
idPage = 1

# List of pages that are not marked (like instructions, formula sheets, etc)
# Leave as an empty list '[]' if no such pages
doNotMarkPages = []

# The information for each question starts with '[[question]]'.
# For each we must give the list of pages and the maximum mark.
# We have given some default values, but these must be edited
# and then uncomment them by removing the leading #'s.
#
# Then, optionally, give a label for the question, such as
# 'label = "Ex3"
# By default Plom generates labels for you.
#
# Then, also optionally, tell Plom how to select the question from the
# available versions - either
#    'select = "shuffle"' - take randomly from any version, or
#    'select = "fix"' - always take from version 1
# By default Plom will use "shuffle"
"""

        score_per_question = score // questions
        pages_per_question = (pages - 1) // questions
        question_scores = [score_per_question for qi in range(questions)]
        question_pages = [
            [2 + qi * pages_per_question + pn for pn in range(pages_per_question)]
            for qi in range(questions)
        ]
        # fix up score and pages for last question
        question_scores[-1] += score - sum(question_scores)
        question_pages[-1] += [pn + 1 for pn in range(question_pages[-1][-1], pages)]

        for k in range(questions):
            spec_toml += f"""
[[question]]
## "pages" = {question_pages[k]}  ## <<<<< This needs editing
## "mark"= {question_scores[k]}  ## <<<<< This needs editing
"""
        return spec_toml
