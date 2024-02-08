# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Andrew Rechnitzer
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2023-2024 Colin B. Macdonald

from django.db import models

from Base.models import SingletonBaseModel


class SpecQuestion(models.Model):
    """A question in the test specification."""

    pages = models.JSONField()
    mark = models.PositiveIntegerField(null=False)
    select = models.CharField(
        choices=[("fix", "fix"), ("shuffle", "shuffle")],
        default="shuffle",
        max_length=7,  # length of the string "shuffle"
    )
    label = models.TextField(null=True)
    # TODO: rename to question_index, Issue #3264, Issue #2716.
    question_number = models.PositiveIntegerField(null=False, unique=True)


class Specification(SingletonBaseModel):
    """Store the json of the test specification dictionary.

    There can be at most one Specification entry.
    """

    name = models.TextField(null=False)
    longName = models.TextField(null=False)
    numberOfVersions = models.PositiveIntegerField(null=False)
    numberOfPages = models.PositiveIntegerField(null=False)
    numberOfQuestions = models.PositiveIntegerField(null=False)
    totalMarks = models.PositiveIntegerField(null=False)
    privateSeed = models.TextField()
    publicCode = models.TextField()
    idPage = models.PositiveIntegerField()
    doNotMarkPages = models.JSONField()

    def __getattr__(self, name):
        """If querying for questions, return a dictionary of all the spec questions."""
        if name == "question":
            return self.get_question_dict()
        else:
            raise AttributeError(f"Member {name} not found in test specification.")

    def get_question_dict(self):
        """Return all the questions in the form of a dictionary, where keys are question numbers."""
        return {str(q.question_number): q for q in SpecQuestion.objects.all()}

    def get_question_list(self):
        """Return the questions in the form of a list."""
        return list(SpecQuestion.objects.all())


class SolnSpecQuestion(models.Model):
    """A solution to a question in the solution specification."""

    pages = models.JSONField()
    solution_number = models.PositiveIntegerField(null=False, unique=True)


class SolnSpecification(SingletonBaseModel):
    """Store the json of the solution specification dictionary.

    Note that
      * There can be at most one SolutionSpecification entry
      * The number of versions is given by the test spec - so not in soln spec
      * The number of questions is given by test spec - so not in soln spec

    numberOfPages (int): The number of pages in the solution.
    """

    numberOfPages = models.PositiveIntegerField(null=False)

    def __getattr__(self, name):
        """If querying for solution, return a dictionary of all the soln-spec solutions."""
        if name == "solution":
            return self.get_solution_dict()
        else:
            raise AttributeError(f"Member {name} not found in solution Specification.")

    def get_solution_dict(self):
        """Return all the solution questions in the form of a dictionary, where keys are question numbers."""
        return {str(s.solution_number): s for s in SolnSpecQuestion.objects.all()}

    def get_soltion_list(self):
        """Return the solution questions in the form of a list."""
        return list(SolnSpecQuestion.objects.all())
